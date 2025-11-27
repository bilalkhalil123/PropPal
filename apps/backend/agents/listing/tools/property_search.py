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
    Search properties using vector similarity search with Qdrant.
    
    Args:
        query: Search query text
        k: Number of results to return
        
    Returns:
        Dictionary containing search results
    """
    import logging
    logger = logging.getLogger(__name__)
    
    client = None
    try:
        if not query:
            return {"success": True, "query": query, "results": [], "count": 0}
        
        from bson import ObjectId
        from services.vector_search.qdrant_service import search_properties as qdrant_search_properties
        
        logger.info(f"[PROPERTY_SEARCH] Searching for: {query}")
        
        # Generate query embedding
        query_vec = embed_text(query)
        logger.info(f"[PROPERTY_SEARCH] Generated embedding, dimension: {len(query_vec)}")
        
        # Search in Qdrant
        qdrant_results = await qdrant_search_properties(
            query_vector=query_vec,
            limit=k,
            filters=None,
        )
        
        logger.info(f"[PROPERTY_SEARCH] Qdrant returned {len(qdrant_results)} results")
        
        if not qdrant_results:
            logger.warning(f"[PROPERTY_SEARCH] No results from Qdrant for query: {query}")
            return {
                "success": True,
                "query": query,
                "results": [],
                "count": 0
            }
        
        # Get database client and database
        client = get_database_client()
        db = client["proppal"]
        
        # Extract property IDs from Qdrant results
        property_ids = []
        for result in qdrant_results:
            prop_id = result.get("id")
            if prop_id:
                try:
                    property_ids.append(ObjectId(prop_id))
                except Exception as e:
                    logger.error(f"[PROPERTY_SEARCH] Invalid ObjectId: {prop_id}, error: {e}")
                    continue
        
        logger.info(f"[PROPERTY_SEARCH] Extracted {len(property_ids)} valid property IDs")
        
        if not property_ids:
            logger.warning(f"[PROPERTY_SEARCH] No valid property IDs extracted from Qdrant results")
            return {
                "success": True,
                "query": query,
                "results": [],
                "count": 0
            }
        
        # Fetch properties from MongoDB
        properties_cursor = db["properties"].find(
            {"_id": {"$in": property_ids}},
            {
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
        )
        
        properties = await properties_cursor.to_list(length=k)
        logger.info(f"[PROPERTY_SEARCH] Fetched {len(properties)} properties from MongoDB")
        
        # Create a map of _id to score for ordering
        score_map = {result["id"]: result["score"] for result in qdrant_results}
        
        # Sort results by Qdrant score and add score to results
        results = []
        for prop in properties:
            prop_id_str = str(prop["_id"])
            if prop_id_str in score_map:
                prop["_id"] = prop_id_str
                prop["score"] = score_map[prop_id_str]
                results.append(prop)
        
        # Sort by score (descending)
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        logger.info(f"[PROPERTY_SEARCH] Returning {len(results)} results")
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        import traceback
        logger.error(f"[PROPERTY_SEARCH] Error: {str(e)}")
        logger.error(f"[PROPERTY_SEARCH] Traceback: {traceback.format_exc()}")
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
