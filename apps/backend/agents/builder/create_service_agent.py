"""
Specialized sub-agent for creating a new builder service via conversation.
"""

import logging
import os
from dotenv import load_dotenv
import json
from langchain_groq import ChatGroq
from typing import Optional
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

        # UPDATED: This prompt is simplified to remove ambiguity.
        self.system_prompt = """You are a "Service Creation Assistant". Your goal is to help a builder create a new service listing by filling in a JSON dictionary.

CRITICAL INSTRUCTIONS:
- You will be given the user's conversation history and the current state of a `service_data` JSON object.
- **Your Response Format:** Unless calling the tool, your response MUST be a single JSON object with three keys: `status` ('continue', 'confirming', or 'cancelled'), `updated_data` (the fully updated data object), and `response`.

**STATE-BASED CONVERSATIONAL FLOW:**

**1. FIRST, CHECK FOR CONFIRMATION:**
    - Look at the `Conversation History`. Was the *very last* agent message a confirmation question (e.g., "Should I proceed?")?
    - **IF YES (Awaiting Confirmation):**
        - **And the user's new message is affirmative** ("yes", "proceed", "continue", "yep"):
            - Your *only* job is to call the `create_builder_service_tool`.
            - Do NOT respond with JSON. Do NOT say anything. Just call the tool.
        - **And the user's new message is negative or asks for a change** ("no", "wait", "change the description"):
            - Set `status` to "continue".
            - **CRITICAL:** "no" means "do not proceed", it does NOT mean "cancel".
            - In `response`, ask "Got it. What specifically would you like to update?"
        - **And the user's new message is unclear:**
            - Set `status` to "confirming".
            - In `response`, repeat the question: "Sorry, I didn't get that. Should I proceed with creating the service?"

**2. IF NOT AWAITING CONFIRMATION, GATHER DATA:**
    - **a. Data Extraction:** Analyze the user's most recent message and update the `service_data` object.
    - **b. Data Validation:**
        - `base_price` MUST be a number. Convert valid number strings (e.g., "125") to numbers (e.g., 125). If invalid, ask again.
        - `service_features` MUST be a list of strings. Convert comma-separated strings (e.g., "feat 1, feat 2") to `["feat 1", "feat 2"]`.
    - **c. Find Next Question:** Find the first `null` value in this EXACT field order:
        1. `title`
        2. `description`
        3. `category`
        4. `base_price`
        5. `price_unit` (When asking, suggest examples: "per hour, per sqft, or a fixed price")
        6. `estimated_duration` (This is optional. When asking, suggest examples: "1 hour, 1 day, or a fixed duration")
        7. `service_features` (This is optional. Ask for a comma-separated list or to 'skip')
    - **d. Ask Question:**
        - If you found a `null` field from the list above, ask the user for *only* that one piece of information.
        - **If the user says "skip"** or "no" for an *optional* field (`estimated_duration`, `service_features`), you MUST keep its value as `null` and move to the *next* field in the list (or to confirmation).
    - **e. Start Confirmation:** ONLY when you have checked all 7 fields (and they are either filled or skipped):
        - Set `status` to "confirming".
        - Summarize all collected data (ignoring `null` values) in your `response`.
        - End the `response` with a clear question: "I have these details: [summary]. Should I proceed?"

**3. CANCELLATION & UPDATES:**
    - If the user wants to cancel, quit, or stop at any time, set `status` to "cancelled" and confirm.
    - If the user asks to change a field (e.g., "wait, change the price"), update the data and then ask "Got it. What else would you like to update?" or proceed to the next missing field.

Example (Data Gathering):
User says: "The base price is 5000."
Your output (a single JSON object):
{"status": "continue", "updated_data": {"title": "...", "description": "...", "category": "...", "base_price": 5000, "price_unit": null, ...}, "response": "Got it. What is the price unit, for example: per hour, per sqft, or a fixed price?"}

Example (Starting Confirmation):
User says: "skip features"
Your output (a single JSON object):
{"status": "confirming", "updated_data": {"title": "...", ... "service_features": null}, "response": "Got it. I have the title as '...' and the price as '...'. Should I proceed?"}
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

    def process_query(self, query: str, clerk_id: Optional[str] = None, user_id: Optional[str] = None) -> dict:
        """
        Handles the entire conversational flow for creating a new service.
        It takes an initial query and manages the back-and-forth until completion or cancellation.
        It can accept either a clerk_id or a user_id.
        """
        if not query or not query.strip():
            return {
                "success": False,
                "response": "Please provide a valid query.",
                "error": "Empty query provided"
            }

        # Determine which ID to use. Prioritize clerk_id.
        id_to_use = clerk_id if clerk_id else user_id
        id_type = "clerk_id" if clerk_id else "user_id"

        if not id_to_use:
            return {
                "success": False,
                "response": "User could not be identified. Cannot create a service.",
                "error": "Missing clerk_id and user_id"
            }

        # **Step 1: Verify if the user has a builder profile before starting.**
        profile_check = check_builder_profile_exists(clerk_id=clerk_id, user_id=user_id)
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

            User Context: The user's {id_type} is '{id_to_use}'. You must use this ID when calling the create_builder_service_tool.
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
                
                # UPDATED: Re-written logic to handle both tool calls and JSON responses
                
                final_message = final_state["messages"][-1]
                final_response_content = final_message.content

                # Default values
                response_for_user = "I'm sorry, I seem to have gotten stuck. Could you please repeat that?"
                conversation_status = "continue"

                # CASE 1: The tool was called. This is the end of the conversation.
                # The final_message.role will be 'tool' and its content is the tool's return value.
                if final_message.type == "tool":
                    try:
                        # Try to parse tool output as JSON
                        tool_result = json.loads(final_response_content)
                        response_for_user = tool_result.get("message", "Service created successfully!")
                        conversation_status = "completed"
                        final_state["success"] = tool_result.get("success", True)
                        final_state["error"] = tool_result.get("error", None)
                    except json.JSONDecodeError:
                        # Tool returned a simple string, not JSON
                        response_for_user = final_response_content
                        conversation_status = "completed"
                        final_state["success"] = True # Assume success if tool ran
                
                # CASE 2: The LLM returned a JSON object to continue the conversation.
                # The final_message.role will be 'ai' (or 'assistant').
                else:
                    try:
                        parsed_json = json.loads(final_response_content)
                        response_for_user = parsed_json.get("response", response_for_user)
                        service_data = parsed_json.get("updated_data", service_data)
                        conversation_status = parsed_json.get("status", "continue")
                    except json.JSONDecodeError:
                        # This was your "loop" bug. The LLM didn't return JSON or call a tool.
                        logger.warning(f"LLM did not return valid JSON. Response: {final_response_content}")
                        
                        # Try to recover gracefully
                        if "Should I proceed?" in conversation_history:
                            response_for_user = "Sorry, I didn't get that. Should I proceed with creating the service?"
                            conversation_status = "confirming"
                        else:
                            response_for_user = "I didn't quite understand that. Could you please clarify?"
                            conversation_status = "continue"

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