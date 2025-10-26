"""
Specialized sub-agent for creating a new builder service via conversation.
"""

import logging
import os
from dotenv import load_dotenv
import json
from langchain_groq import ChatGroq
from langgraph.prebuilt import ToolNode
from agents.listing.agent import AgentState, ListingAgent # Re-using the graph structure
from .tools import create_builder_service_tool, check_builder_profile_exists

# Load .env file
load_dotenv()

logger = logging.getLogger(__name__)

class BuilderServiceCreationAgent(ListingAgent):
    """
    An agent that guides a builder through creating a new service.
    It inherits the graph structure from ListingAgent but uses its own prompt and tools.
    """

    def __init__(self, model_name: str = "llama-3.1-8b-instant"):

        self.system_prompt = """You are a "Service Creation Assistant". Your goal is to help a builder create a new service listing by filling in a JSON dictionary.

CRITICAL INSTRUCTIONS:
- You will be given the user's conversation history and the current state of a `service_data` JSON object.
- **Your First Task:** Analyze the user's most recent message and update the `service_data` object with any new information they provided. The user might provide multiple details at once.
- **Data Validation:**
  - `base_price` MUST be a number. If the user provides text, tell them it's invalid and ask again. Convert valid number strings (e.g., "125") to numbers (e.g., 125) in the JSON.
  - `service_features` MUST be a list of strings. If the user provides a comma-separated string, convert it to a list (e.g., "a, b" becomes `["a", "b"]`). If they say "no" or "skip", leave the value as `null`.
- **Your Second Task (Decision Flow):** Follow this sequence strictly.
  1.  **Gather Required Info:** Check for the first `null` value in the **required** fields (`title`, `description`, `category`, `base_price`, `price_unit`) and ask the user for it. Do not proceed until all are filled.
  2.  **Gather Optional Info:** Once all required fields are filled, check for the first `null` value in the **optional** fields (`estimated_duration`, `service_features`) and ask for it. If the user skips, that's fine; you will move to the next step in the next turn.
  3.  **Confirm with User:** Once all required fields are filled AND you have asked about all optional fields (i.e., you are at the end of the list), you MUST enter the `confirming` state. Summarize all collected data (ignoring `null` values) and ask for final confirmation (e.g., "I have these details: ... Should I proceed?").
  4.  **Call the Tool:** ONLY if the user has just confirmed the details (e.g., said "yes" or "proceed"), you MUST call the `create_builder_service_tool`. Do not respond with JSON; just call the tool.
- **Your Response Format:** Unless calling the tool, your response MUST be a single JSON object with three keys: `status` ('continue', 'confirming', or 'cancelled'), `updated_data` (the fully updated data object), and `response`.
- The `clerk_id` is provided in the context; do not ask the user for it.
- If the user wants to cancel, quit, or stop, set `status` to "cancelled" and provide a confirmation message in `response`.

Example:
User says: "The title is 'Expert Plumbing' and it's in the 'MEP' category."
Your output (a single JSON object):
{"status": "continue", "updated_data": {"title": "Expert Plumbing", "description": null, "category": "MEP", ...}, "response": "Got it. Now, could you provide a description?"}
"""

        # 2. Define the tools this agent can use
        self.tools = [create_builder_service_tool]

        # 3. Create the tool executor
        self.tool_executor = ToolNode(self.tools)

        # 4. Initialize the LLM
        self.llm = ChatGroq(
            model=model_name,
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.2
        )

        # 5. Bind the new tools to the LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # 6. Create the graph (re-using the parent's method)
        self.graph = self._create_graph()
        self.app = self.graph.compile()

    def process_query(self, query: str, clerk_id: str) -> dict:
        """
        Handles the entire conversational flow for creating a new service.
        It takes an initial query and manages the back-and-forth until completion or cancellation.
        """
        if not query or not query.strip():
            return {
                "success": False,
                "response": "Please provide a valid query.",
                "error": "Empty query provided"
            }
        if not clerk_id:
            return {
                "success": False,
                "response": "User could not be identified. Cannot create a service.",
                "error": "Missing clerk_id"
            }

        # **Step 1: Verify if the user has a builder profile before starting.**
        profile_check = check_builder_profile_exists(clerk_id)
        if not profile_check["exists"]:
            return {"success": False, "response": profile_check["error"], "error": profile_check["error"]}

        # Initialize conversation state
        conversation_history = f"User: {query}\n"
        service_data = {
            "title": None,
            "description": None,
            "category": None,
            "base_price": None,
            "price_unit": None,
            "estimated_duration": None,
            "service_features": None,
        }

        while True:
            # We inject the clerk_id and the current state of service_data into the context for the agent.
            prompt_for_llm = f"""
            Conversation History:
            {conversation_history}

            Current Data State (JSON):
            {json.dumps(service_data)}

            User Context: The user's clerk_id is '{clerk_id}'. You must use this ID when calling the create_builder_service_tool.
            """

            initial_state = AgentState(
                messages=[{"role": "user", "content": prompt_for_llm.strip()}],
                query=conversation_history.strip(),
                data={"service_data": service_data}, # Pass the dictionary in the agent state
                error=None,
                success=False,
                response=""
            )

            try:
                # This agent will require multiple steps to gather all info.
                final_state = self.app.invoke(initial_state, {"recursion_limit": 10})
                final_response_content = final_state["messages"][-1].content
                
                # Default values
                response_for_user = "I'm sorry, I seem to have gotten stuck. Could you please repeat that?"
                conversation_status = "continue"

                # Check if the tool was called (which means we are done)
                if final_state.get("success"):
                    response_for_user = final_response_content
                    conversation_status = "completed"
                else:
                    # If the tool was not called, parse the JSON response from the LLM
                    try:
                        parsed_json = json.loads(final_response_content)
                        response_for_user = parsed_json.get("response", response_for_user)
                        service_data = parsed_json.get("updated_data", service_data)
                        conversation_status = parsed_json.get("status", "continue")
                    except json.JSONDecodeError:
                        logger.warning(f"LLM did not return valid JSON for state update. Response: {final_response_content}")
                        response_for_user = "I didn't quite understand that. Could you please clarify?"

                print(f"🤖 Agent: {response_for_user}")
                conversation_history += f"Agent: {response_for_user}\n"

                if conversation_status in ["completed", "cancelled", "failed"]:
                    print("\n--- Conversation Ended ---")
                    return {
                        "success": final_state.get("success", False),
                        "response": response_for_user,
                        "status": conversation_status,
                        "error": final_state.get("error")
                    }

                user_input = input("> You: ")
                if user_input.lower() in ["quit", "exit", "cancel"]:
                    user_input = "I want to cancel this process."

                conversation_history += f"User: {user_input}\n"

            except Exception as e:
                logger.error(f"BuilderServiceCreationAgent loop failed: {e}")
                return {
                    "success": False,
                    "response": f"An unexpected error occurred: {str(e)}",
                    "error": str(e)
                }
