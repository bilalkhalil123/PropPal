"""
Specialized sub-agent for searching builder profiles and services.
"""

import logging
import json
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.prebuilt import ToolNode
from agents.listing.agent import ListingAgent, AgentState # Re-using the graph structure
from .tools import builder_profile_search_tool, builder_service_search_tool

# Load .env file
load_dotenv()

logger = logging.getLogger(__name__)

class BuilderSearchAgent(ListingAgent):
    """
    A specialized agent for searching builders and their services.
    It inherits the graph structure from ListingAgent but uses its own prompt and tools.
    """
    
    def __init__(self, model_name: str = "llama-3.1-8b-instant"):
        
        # 1. Define the specific role and instructions for this agent
        self.system_prompt = """You are a Builder Search Agent for PropPal.

Your only job is to help users find builders or builder services.

CRITICAL INSTRUCTIONS:
- If the user is looking for a builder, company, or contractor, you MUST immediately call the `builder_profile_search_tool`.
- If the user is looking for a specific service (like 'plumbing', 'remodeling', 'construction'), you MUST immediately call the `builder_service_search_tool`.
- Do NOT ask clarifying questions. Use the tool that best matches the user's query.
- After using a tool, present the results clearly. If nothing is found, say so politely.
- If you don't find any relevant builders or services, inform the user that no matches were found.

For general conversation (like "hello"), respond naturally without using tools.
"""
        
        # 2. Define the tools this agent can use
        self.tools = [builder_profile_search_tool, builder_service_search_tool]
        
        # 3. Create the tool executor with the new tools, consistent with parent class
        self.tool_executor = ToolNode(self.tools)
        
        # 4. Initialize the LLM
        self.llm = ChatGroq(
            model=model_name,
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1
        )
        
        # 5. Bind the new tools to the LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # 6. Create the graph (re-using the parent's method)
        self.graph = self._create_graph()
        self.app = self.graph.compile()

    def process_query(self, query: str) -> dict:
        """
        Process a builder/service search query and format the output correctly.
        This overrides the parent ListingAgent's method to return a generic 'results' key.
        """

        print("query given: ", query.strip())
        if not query or not query.strip():
            return {
                "success": False,
                "response": "Please provide a valid search query.",
                "results": [],
                "count": 0,
                "error": "Empty query provided"
            }

        initial_state = AgentState(
            messages=[{"role": "user", "content": query.strip()}],
            query=query.strip(),
            data={},
            error=None,
            success=False,
            response=""
        )

        try:
            final_state = self.app.invoke(initial_state, {"recursion_limit": 5})
            final_response = final_state["messages"][-1].content
            data = final_state.get("data", {})

            print("final response:", final_response)
            return {
                "success": final_state.get("success", False),
                "response": final_response,
                "results": data.get("results", []),
                "count": data.get("count", 0),
                "error": final_state.get("error")
            }
        except Exception as e:
            logger.error(f"BuilderSearchAgent graph invocation failed: {e}")
            return {
                "success": False,
                "response": f"An unexpected error occurred: {str(e)}",
                "results": [],
                "count": 0,
                "error": str(e)
            }
