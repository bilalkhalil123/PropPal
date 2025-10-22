"""
Listing Agent for property search using LangGraph.
"""

from typing import Any, Dict
from agents.base.agent import BaseAgent, AgentState
from agents.listing.tools import property_search_tool


class ListingAgent(BaseAgent):
    """Agent for property search operations."""
    
    def __init__(self):
        system_prompt = """You are a Property Search Agent for PropPal.
        
        Help users find properties by understanding their search criteria
        and using the property search tool to find matching listings.
        
        When users ask about properties, use the property_search_tool with their query."""
        
        super().__init__(
            name="ListingAgent",
            system_prompt=system_prompt,
            tools=[property_search_tool]
        )
    
    def _format_tool_response(self, state: AgentState) -> str:
        """Format property search results into a helpful response."""
        data = state.get("data", {})
        
        if data.get("success"):
            count = data.get("count", 0)
            if count > 0:
                return f"I found {count} properties matching your search. Here are the results:"
            else:
                return "I couldn't find any properties matching your criteria. Try adjusting your search terms or location."
        else:
            return "I encountered an issue while searching for properties. Please try again."
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Process a property search query."""
        result = super().process_query(query)
        
        # Extract property data
        properties = result.get("data", {}).get("results", [])
        count = result.get("data", {}).get("count", 0)
        
        return {
            "success": result["success"],
            "response": result.get("response", ""),
            "properties": properties,
            "count": count,
            "error": result.get("error")
        }
