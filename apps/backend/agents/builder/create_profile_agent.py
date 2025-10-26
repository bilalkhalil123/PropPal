"""
Specialized sub-agent for creating a new builder profile via conversation.
"""

import logging
import os
from dotenv import load_dotenv
import json
from langchain_groq import ChatGroq
from langgraph.prebuilt import ToolNode
from agents.listing.agent import AgentState, ListingAgent # Re-using the graph structure
from .tools import create_builder_profile_tool, check_builder_profile_exists

# Load .env file
load_dotenv()

logger = logging.getLogger(__name__)

class BuilderProfileCreationAgent(ListingAgent):
    """
    An agent that guides a user through creating their builder profile.
    It inherits the graph structure from ListingAgent but uses its own prompt and tools.
    """

    def __init__(self, model_name: str = "llama-3.1-8b-instant"):

        # 1. UPDATED: Stricter, state-based system prompt
        self.system_prompt = """You are a "Builder Profile Onboarding Assistant". Your goal is to help a user create their builder profile by filling in a JSON dictionary.

MASTER RULE: You have two modes.
1.  **GATHERING DATA:** Your response MUST be a single JSON object (`status`, `updated_data`, `response`). You MUST NOT call any tools in this mode.
2.  **CALLING TOOL:** This mode is ONLY for when the user has confirmed all details. Your response MUST be *only* a tool call. You MUST NOT respond with JSON.
You must choose one mode. You cannot do both.

CRITICAL INSTRUCTIONS:
- You will be given the user's conversation history and the current state of a `profile_data` JSON object.
- **Your Response Format:** As per the MASTER RULE, your response is either a single JSON object OR a single tool call.

**STATE-BASED CONVERSATIONAL FLOW:**

**1. FIRST, CHECK FOR CONFIRMATION:**
    - Look at the `Conversation History`. Was the *very last* agent message a confirmation question (e.g., "Should I proceed?")?
    - **IF YES (Awaiting Confirmation):**
        - **And the user's new message is affirmative** ("yes", "proceed", "continue", "yep"):
            - **Enter "CALLING TOOL" mode.**
            - Your *only* job is to call the `create_builder_profile_tool`. Do NOT respond with JSON.
        - **And the user's new message is negative or asks for a change** ("no", "wait", "change the city"):
            - **Enter "GATHERING DATA" mode.**
            - Set `status` to "continue".
            - In `response`, ask "Got it. What specifically would you like to update?"
        - **And the user's new message is unclear:**
            - **Enter "GATHERING DATA" mode.**
            - Set `status` to "confirming". (This keeps them in the confirmation loop)
            - In `response`, repeat the question: "Sorry, I didn't get that. Should I proceed with creating the profile?"

**2. IF NOT AWAITING CONFIRMATION, GATHER DATA:**
    - **You MUST be in "GATHERING DATA" mode.** Do NOT call any tools.
    - **a. Data Extraction:** Analyze the user's most recent message and update the `profile_data` object.
    - **b. Data Validation:**
        - `experience_years` MUST be a number. Convert valid number strings (e.g., "5") to numbers (e.g., 5). If invalid, ask again.
        - `specialization` MUST be a list of strings. **If the user provides a single item (e.g., "roofing"), convert it to a list (e.g., `["roofing"]`).** If they provide a comma-separated string (e.g., "a, b"), convert it to `["a", "b"]`.
    - **c. Find Next Question:** Find the first `null` value in this EXACT field order:
        1. `company_name`
        2. `city`
        3. `specialization` (When asking, suggest examples: "e.g., residential construction, kitchen remodeling")
        4. `experience_years` (When asking, say: "e.g., 5, 10")
        5. `about` (When asking, say: "a brief description of your company")
    - **d. Ask Question:**
        - If you found a `null` field from the list above, ask the user for *only* that one piece of information.
    - **e. Start Confirmation:** ONLY when you have checked all 5 fields and they are all filled:
        - Set `status` to "confirming".
        - Summarize all collected data in your `response`.
        - End the `response` with a clear question: "I have these details: [summary]. Should I proceed?"

**3. CANCELLATION:**
    - If the user wants to cancel, quit, or stop at any time, set `status` to "cancelled" and confirm.
"""

        # 2. Define the tools this agent can use
        self.tools = [create_builder_profile_tool]

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

    def process_query(self, query: str, clerk_id: str = None, user_id: str = None) -> dict:
        """
        Handles the entire conversational flow for creating a new profile.
        It can accept either a clerk_id or a user_id.
        """
        if not query or not query.strip():
            return {"success": False, "response": "Please provide a valid query.", "error": "Empty query"}
        
        # Determine which ID to use. Prioritize clerk_id.
        id_to_use = clerk_id if clerk_id else user_id
        id_type = "clerk_id" if clerk_id else "user_id"

        if not id_to_use:
            return {"success": False, "response": "User could not be identified. Cannot create a profile.", "error": "Missing clerk_id and user_id"}

        # **Step 1: Verify if the user already has a builder profile.**
        profile_check = check_builder_profile_exists(clerk_id=clerk_id, user_id=user_id)
        if profile_check["exists"]:
            return {"success": False, "response": "A builder profile already exists for this user. You can only have one.", "error": "Profile already exists"}

        # Initialize conversation state
        conversation_history = f"User: {query}\n"
        profile_data = {
            "company_name": None,
            "specialization": None,
            "experience_years": None,
            "about": None,
            "city": None,
        }

        while True:
            prompt_for_llm = f"""
            Conversation History:
            {conversation_history}

            Current Data State (JSON):
            {json.dumps(profile_data)}

            User Context: The user's {id_type} is '{id_to_use}'. You must use this ID when calling the create_builder_profile_tool.
            """

            initial_state = AgentState(
                messages=[{"role": "user", "content": prompt_for_llm.strip()}],
                query=conversation_history.strip(),
                data={"profile_data": profile_data},
                error=None,
                success=False,
                response=""
            )

            # 2. UPDATED: New `try/except` block logic
            try:
                final_state = self.app.invoke(initial_state, {"recursion_limit": 10})
                
                final_message = final_state["messages"][-1]
                final_response_content = final_message.content

                # Default values
                response_for_user = "I'm sorry, I seem to have gotten stuck. Could you please repeat that?"
                conversation_status = "continue"

                # CASE 1: The tool was called. This is the end of the conversation.
                # The final_message.type will be 'tool' and its content is the tool's return value.
                if final_message.type == "tool":
                    try:
                        # Try to parse tool output as JSON
                        tool_result = json.loads(final_response_content)
                        response_for_user = tool_result.get("message", "Profile created successfully!")
                        conversation_status = "completed"
                        final_state["success"] = tool_result.get("success", True)
                        final_state["error"] = tool_result.get("error", None)
                    except json.JSONDecodeError:
                        # Tool returned a simple string (or an error string)
                        response_for_user = final_response_content
                        # If the tool content includes 'Error code:', it was a failure.
                        if "Error code:" in final_response_content:
                             conversation_status = "failed"
                             final_state["success"] = False
                             final_state["error"] = final_response_content
                        else:
                             conversation_status = "completed"
                             final_state["success"] = True

                # CASE 2: The LLM returned a JSON object to continue the conversation.
                # The final_message.type will be 'ai' (or 'assistant').
                else:
                    try:
                        parsed_json = json.loads(final_response_content)
                        response_for_user = parsed_json.get("response", response_for_user)
                        profile_data = parsed_json.get("updated_data", profile_data) # <-- Corrected to profile_data
                        conversation_status = parsed_json.get("status", "continue")
                    except json.JSONDecodeError:
                        # This was your "loop" bug. The LLM didn't return JSON or call a tool.
                        logger.warning(f"LLM did not return valid JSON for state update. Response: {final_response_content}")
                        
                        # Try to recover gracefully
                        if "Should I proceed?" in conversation_history:
                            response_for_user = "Sorry, I didn't get that. Should I proceed with creating the profile?"
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
                logger.error(f"BuilderProfileCreationAgent loop failed: {e}", exc_info=True)
                return {"success": False, "response": f"An unexpected error occurred: {str(e)}", "error": str(e)}