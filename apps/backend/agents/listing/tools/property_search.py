"""
Property search tool for the Listing Agent.
"""
import asyncio
from typing import Any, Dict, List
from langchain_core.tools import tool
from motor.motor_asyncio import AsyncIOMotorClient
from services.embeddings.service import embed_text
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_client():
    """Create a fresh database client for each request."""
    mongodb_url = os.getenv("MONGODB_URL")
    if not mongodb_url:
        raise ValueError("MONGODB_URL environment variable is required")
    return AsyncIOMotorClient(mongodb_url)

async def _search_properties_async(query: str, k: int = 5) -> Dict[str, Any]:
    """
    Search properties using vector similarity search directly.
    
    Args:
        query: Search query text
        k: Number of results to return
        
    Returns:
        Dictionary containing search results
    """
    client = None
    try:
        if not query:
            return {"success": True, "query": query, "results": [], "count": 0}
        
        # Get database client and database
        client = get_database_client()
        db = client["proppal"]
        
        # Generate query embedding
        query_vec = embed_text(query)
        
        # Build vector search pipeline
        pipeline: List[Dict[str, Any]] = [
            {
                "$vectorSearch": {
                    "index": "properties_embedding_index",
                    "path": "embedding",
                    "queryVector": query_vec,
                    "numCandidates": max(500, k * 10),
                    "limit": k,
                }
            },
            {
                "$project": {
                    "score": {"$meta": "vectorSearchScore"},
                    "title": 1,
                    "price": 1,
                    "city": 1,
                    "area": 1,
                    "property_type": 1,
                    "bedrooms": 1,
                    "bathrooms": 1,
                    "area_sqft": 1,
                    "images": 1,
                }
            },
        ]
        
        # Execute search
        results = await db["properties"].aggregate(pipeline).to_list(k)
        
        # Normalize _id for JSON serialization
        for r in results:
            if "_id" in r:
                r["_id"] = str(r["_id"])
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": [],
            "count": 0
        }
    finally:
        # Always close the database client
        if client:
            client.close()

@tool
def property_search_tool(query: str) -> Dict[str, Any]:
    """
    Search for properties using direct database vector search.
    
    Args:
        query: Search query text
        
    Returns:
        Dictionary containing search results
    """
    try:
        # Try to get the current event loop, or create a new one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Event loop is closed")
        except RuntimeError:
            # No event loop exists, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            should_close = True
        else:
            should_close = False
        
        try:
            if loop.is_running():
                # If we're in an async context, we need to use a different approach
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, _search_properties_async(query, k=5))
                    result = future.result()
            else:
                result = loop.run_until_complete(_search_properties_async(query, k=5))
            return result
        finally:
            if should_close:
                loop.close()
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": [],
            "count": 0
        }
