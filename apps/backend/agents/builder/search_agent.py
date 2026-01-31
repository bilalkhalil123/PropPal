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

Your ONLY job is to help users find builders or builder services by using the search tools.

CRITICAL INSTRUCTIONS - YOU MUST FOLLOW THESE:
1. ALWAYS call a tool for search queries. NEVER respond without calling a tool.
2. If the user is looking for a builder, company, or contractor, you MUST call `builder_profile_search_tool` with their exact query.
3. If the user is looking for a specific service (like 'plumbing', 'remodeling', 'construction', 'interior design'), you MUST call `builder_service_search_tool` with their exact query.
4. Do NOT ask clarifying questions. Do NOT explain what you're doing. Just call the appropriate tool immediately.
5. After the tool returns results, format them clearly for the user.
6. If no results are found, say "No matches were found for [query]. Please try different search terms."

IMPORTANT: If you don't call a tool, you have FAILED. Always call a tool for search queries.

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
        Filters are now extracted automatically by the tools themselves.
        """
        try:
            logger.info(f"BuilderSearchAgent tool node called")
            
            # Call the parent's tool executor
            # The tools will extract filters from the query automatically
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
                        content = msg.content
                        if isinstance(content, dict):
                            tool_data = content
                        else:
                            tool_data = json.loads(content) if isinstance(content, str) else {}
                    except json.JSONDecodeError:
                        try:
                            import ast
                            tool_data = ast.literal_eval(content) if isinstance(content, str) else {}
                        except Exception:
                            continue
                    try:
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
                                elif any(k in item for k in ["title", "service_name", "builder_id", "category", "price_range_min", "price_range_max", "base_price"]):
                                    # Map title to service_name for frontend compatibility
                                    if "title" in item and "service_name" not in item:
                                        item["service_name"] = item["title"]
                                    services.append(item)
                            
                            data_result = {
                                "builders": builders,
                                "services": services,
                                "count": len(builders) + len(services)
                            }
                            success = True
                            break
                    except Exception as e:
                        logger.warning(f"Failed to parse tool message: {e}")
                        continue

            # Generate a response message based on results
            if success:
                builders_count = len(data_result.get("builders", []))
                services_count = len(data_result.get("services", []))
                total_count = builders_count + services_count
                
                if total_count == 0:
                    response_text = f"No matches were found for '{state.get('query', 'your query')}'. Please try different search terms."
                elif builders_count > 0 and services_count > 0:
                    response_text = f"Found {builders_count} builder{'s' if builders_count != 1 else ''} and {services_count} service{'s' if services_count != 1 else ''} matching your search."
                elif builders_count > 0:
                    response_text = f"Found {builders_count} builder{'s' if builders_count != 1 else ''} matching your search."
                elif services_count > 0:
                    response_text = f"Found {services_count} service{'s' if services_count != 1 else ''} matching your search."
                else:
                    response_text = "Search completed."
                
                # Add the response message
                from langchain_core.messages import AIMessage
                response_message = AIMessage(content=response_text)
                tool_messages.append(response_message)
            else:
                # If no results, still generate a response
                from langchain_core.messages import AIMessage
                response_message = AIMessage(content=f"No matches were found for '{state.get('query', 'your query')}'. Please try different search terms.")
                tool_messages.append(response_message)
            
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
            final_state = self.app.invoke(initial_state, {"recursion_limit": 12})
            
            # Check if tools were actually called
            messages = final_state.get("messages", [])
            tool_was_called = False
            for msg in messages:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    tool_was_called = True
                    break
                # Also check for ToolMessage
                from langchain_core.messages import ToolMessage
                if isinstance(msg, ToolMessage):
                    tool_was_called = True
                    break
            
            # If no tool was called, force a search (fallback)
            if not tool_was_called:
                logger.warning("No tool was called by the agent, forcing a search")
                # Try to determine which tool to use based on query
                query_lower = query.lower()
                if any(word in query_lower for word in ['service', 'plumbing', 'electrical', 'interior', 'renovation', 'remodeling']):
                    # Likely a service search
                    try:
                        result = builder_service_search_tool.invoke(query)
                        if result.get("success"):
                            services = result.get("results", [])
                            data = {"services": services, "builders": []}
                            final_response = f"Found {len(services)} service{'s' if len(services) != 1 else ''} matching your search." if services else f"No matches were found for '{query}'. Please try different search terms."
                        else:
                            data = {"services": [], "builders": []}
                            final_response = f"No matches were found for '{query}'. Please try different search terms."
                    except Exception as e:
                        logger.error(f"Fallback service search failed: {e}")
                        data = {"services": [], "builders": []}
                        final_response = f"Search completed. No results found for '{query}'."
                else:
                    # Likely a builder search
                    try:
                        result = builder_profile_search_tool.invoke(query)
                        if result.get("success"):
                            builders = result.get("results", [])
                            # Transform city to location.city if needed
                            for item in builders:
                                if "city" in item and "location" not in item:
                                    item["location"] = {"city": item.pop("city")}
                            data = {"builders": builders, "services": []}
                            final_response = f"Found {len(builders)} builder{'s' if len(builders) != 1 else ''} matching your search." if builders else f"No matches were found for '{query}'. Please try different search terms."
                        else:
                            data = {"builders": [], "services": []}
                            final_response = f"No matches were found for '{query}'. Please try different search terms."
                    except Exception as e:
                        logger.error(f"Fallback builder search failed: {e}")
                        data = {"builders": [], "services": []}
                        final_response = f"Search completed. No results found for '{query}'."
            else:
                # Extract the final response from messages
                final_response = "Search completed."
                if messages:
                    # Get the last AI message (should be the response, not a tool call)
                    for msg in reversed(messages):
                        if hasattr(msg, 'content') and msg.content:
                            # Skip tool messages and messages with tool calls
                            if not hasattr(msg, 'tool_calls') or not msg.tool_calls:
                                final_response = msg.content
                                break
                    # Fallback: use the last message's content if no AI message found
                    if final_response == "Search completed." and hasattr(messages[-1], 'content'):
                        final_response = messages[-1].content
                
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
