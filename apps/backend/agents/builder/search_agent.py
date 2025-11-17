"""
Specialized sub-agent for searching builder profiles and services.
"""

import logging
import json
import os
from typing import Dict, Any
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

    def _tool_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Override the parent's tool node to properly categorize builder vs service results.
        """
        try:
            logger.info(f"BuilderSearchAgent tool node called")
            
            # Call the parent's tool executor
            tool_result = self.tool_executor.invoke(state)
            
            # Extract messages from the result
            if isinstance(tool_result, dict) and "messages" in tool_result:
                tool_messages = tool_result["messages"]
            else:
                tool_messages = tool_result

            # Process tool messages and categorize results
            builders = []
            services = []
            data_result = {}
            success = False
            
            from langchain_core.messages import ToolMessage
            
            for msg in tool_messages:
                if isinstance(msg, ToolMessage):
                    try:
                        tool_data = json.loads(msg.content)
                        logger.info(f"Parsed tool data: {tool_data}")
                        if tool_data.get("success"):
                            results = tool_data.get("results", [])
                            
                            # Categorize results based on fields present
                            for item in results:
                                # Transform builder results to match frontend format
                                if "company_name" in item:
                                    # Transform city to location.city if needed
                                    if "city" in item:
                                        if "location" not in item or not item.get("location"):
                                            item["location"] = {"city": item.pop("city")}
                                        elif isinstance(item.get("location"), dict) and "city" not in item["location"]:
                                            item["location"]["city"] = item.pop("city")
                                        elif not isinstance(item.get("location"), dict):
                                            item["location"] = {"city": item.pop("city")}
                                    builders.append(item)
                                # Service results
                                elif any(k in item for k in ["service_name", "builder_id", "category", "price_range_min", "price_range_max"]):
                                    services.append(item)
                            
                            data_result = {
                                "builders": builders,
                                "services": services,
                                "count": len(builders) + len(services)
                            }
                            success = True
                            break
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse tool message as JSON: {e}")
                        continue

            return {
                "messages": tool_messages,
                "data": data_result,
                "success": success
            }
        except Exception as e:
            logger.error(f"BuilderSearchAgent tool node failed: {e}")
            from langchain_core.messages import ToolMessage
            error_message = ToolMessage(content=f"Tool execution failed: {e}", tool_call_id="error_000")
            return {"messages": [error_message], "error": str(e), "success": False}

    def process_query(self, query: str) -> dict:
        """
        Process a builder/service search query and format the output correctly.
        Returns builders and services separately, similar to how properties are returned.
        """

        logger.info(f"BuilderSearchAgent processing query: {query.strip()}")
        if not query or not query.strip():
            return {
                "success": False,
                "response": "Please provide a valid search query.",
                "builders": [],
                "services": [],
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

            # Extract builders and services from data
            builders = data.get("builders", [])
            services = data.get("services", [])
            total_count = len(builders) + len(services)

            logger.info(f"BuilderSearchAgent results: {len(builders)} builders, {len(services)} services")
            
            return {
                "success": final_state.get("success", False),
                "response": final_response,
                "builders": builders,
                "services": services,
                "count": total_count,
                "error": final_state.get("error")
            }
        except Exception as e:
            logger.error(f"BuilderSearchAgent graph invocation failed: {e}")
            return {
                "success": False,
                "response": f"An unexpected error occurred: {str(e)}",
                "builders": [],
                "services": [],
                "count": 0,
                "error": str(e)
            }
