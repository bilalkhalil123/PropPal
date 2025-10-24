"""
Property search tool for the Listing Agent.
"""
import httpx
from typing import Any, Dict
from langchain_core.tools import tool


@tool
def property_search_tool(query: str) -> Dict[str, Any]:
    """
    Search for properties using the search API.
    
    Args:
        query: Search query text
        
    Returns:
        Dictionary containing search results
    """
    try:
        with httpx.Client() as client:
            response = client.post(
                "http://localhost:8000/api/search/properties",
                json={"query": query, "k": 5},
                timeout=120.0
            )
            
            if response.status_code == 200:
                api_result = response.json()
                return {
                    "success": True,
                    "query": query,
                    "results": api_result.get("results", []),
                    "count": api_result.get("count", 0)
                }
            else:
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}",
                    "query": query,
                    "results": [],
                    "count": 0
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": [],
            "count": 0
        }
