"""
Specialized sub-agent for creating a new builder profile via conversation.
"""

import logging
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.prebuilt import ToolNode
from agents.listing.agent import AgentState, ListingAgent # Re-using the graph structure
from .tools import create_builder_profile_tool

# Load .env file
load_dotenv()

logger = logging.getLogger(__name__)

class BuilderProfileCreationAgent(ListingAgent):
    """
    An agent that guides a user through creating their builder profile.
    """

    def __init__(self, model_name: str = "llama-3.1-8b-instant"):

        self.system_prompt = """You are a "Builder Profile Onboarding Assistant" for PropPal.

Your only job is to help a user create their builder profile.

CRITICAL INSTRUCTIONS:
- Your goal is to have a friendly conversation to collect all the necessary information to call the `create_builder_profile_tool`.
- You MUST collect the following required information from the user:
  - `company_name`: The name of their company.
  - `specialization`: A list of their skills (e.g., "construction", "renovation", "interior design"). Ask for this as a comma-separated list.
  - `experience_years`: How many years of experience they have. This must be a number.
  - `about`: A brief description of their company or services.
  - `city`: The primary city where they operate.
- You MUST have the `clerk_id` of the user, which is provided in the context. Do NOT ask the user for it.
- Ask for one piece of information at a time. Be friendly and guide the user.
- Once you have ALL the required information, call the `create_builder_profile_tool`.
- After calling the tool, present the result (success or failure message) to the user and end the conversation.
- The conversation is stateful. Continue from where you left off based on the message history.

Example conversation flow:
1. User: "I want to register as a builder."
2. You: "I can help with that! To get started, what is the name of your company?"
3. User: "My company is called 'Prestige Worldwide Construction'."
4. You: "Great name! What are your areas of specialization? You can list a few, like 'residential construction, commercial development'."
5. User: "We do residential construction and home renovations."
6. You: "Perfect. How many years of experience do you have in the industry?"
7. ...and so on, until all details are gathered.
8. You (after gathering all info): [Calls `create_builder_profile_tool` with all the arguments]
9. You (after tool call): "Congratulations! Your builder profile for 'Prestige Worldwide Construction' has been created."
"""

        self.tools = [create_builder_profile_tool]
        self.tool_executor = ToolNode(self.tools)
        self.llm = ChatGroq(
            model=model_name,
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.2
        )
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.graph = self._create_graph()
        self.app = self.graph.compile()

    def process_query(self, query: str, clerk_id: str) -> dict:
        """
        Processes a profile creation query. Requires the clerk_id.
        """
        if not query or not query.strip():
            return {"success": False, "response": "Please provide a valid query.", "error": "Empty query"}
        if not clerk_id:
            return {"success": False, "response": "User could not be identified.", "error": "Missing clerk_id"}

        initial_query = f"""
        User Query: "{query}"
        User Context: The user's clerk_id is '{clerk_id}'. You must use this ID when calling the create_builder_profile_tool.
        """

        initial_state = AgentState(
            messages=[{"role": "user", "content": initial_query.strip()}],
            query=query.strip(),
            data={},
            error=None,
            success=False,
            response=""
        )

        try:
            # Allow more steps for the conversation
            final_state = self.app.invoke(initial_state, {"recursion_limit": 15})
            final_response = final_state["messages"][-1].content
            data = final_state.get("data", {})

            # The tool call itself sets success/error in its return dict
            tool_call_result = data.get("results", [{}])[0]
            success = tool_call_result.get("success", final_state.get("success", False))
            error = tool_call_result.get("error", final_state.get("error"))

            return {
                "success": success,
                "response": final_response,
                "results": data.get("results", []),
                "error": error
            }
        except Exception as e:
            logger.error(f"BuilderProfileCreationAgent graph invocation failed: {e}")
            return {
                "success": False,
                "response": f"An unexpected error occurred: {str(e)}",
                "error": str(e)
            }