"""
Property search tool for the Listing Agent.

Uses a hybrid approach: filter first in MongoDB, then retrieve filtered properties from Qdrant
and apply similarity search only on those filtered properties.
"""
import asyncio
import concurrent.futures
import traceback
import hashlib
import math
from typing import Any, Dict, List, Optional
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

def _object_id_to_qdrant_id(object_id_str: str) -> int:
    """
    Convert MongoDB ObjectId string to Qdrant-compatible integer ID.
    Uses hash function to convert ObjectId string to unsigned integer.
    """
    hash_obj = hashlib.sha256(object_id_str.encode('utf-8'))
    hash_bytes = hash_obj.digest()[:8]
    point_id = int.from_bytes(hash_bytes, byteorder='big')
    return point_id % (2**63 - 1)

def _build_mongo_filter(filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build MongoDB filter query from extracted filters.
    
    Args:
        filters: Dictionary of filters (city, price_min, price_max, bedrooms, etc.)
        
    Returns:
        MongoDB filter dictionary
    """
    if not filters or not isinstance(filters, dict) or len(filters) == 0:
        return {}
    
    filter_conditions = []
    
    # City filter - case insensitive
    if "city" in filters and filters["city"]:
        city_val = filters["city"].strip()
        filter_conditions.append({"city": {"$regex": f"^{city_val}$", "$options": "i"}})
    
    # Area filter - partial match
    if "area" in filters and filters["area"]:
        area_val = filters["area"].strip()
        filter_conditions.append({"area": {"$regex": area_val, "$options": "i"}})
    
    # Property type filter
    if "property_type" in filters and filters["property_type"]:
        prop_type = filters["property_type"].strip().lower()
        filter_conditions.append({"property_type": {"$regex": f"^{prop_type}$", "$options": "i"}})
    
    # Price filters
    price_filter = {}
    if "price_min" in filters and filters["price_min"] is not None:
        price_filter["$gte"] = filters["price_min"]
    if "price_max" in filters and filters["price_max"] is not None:
        price_filter["$lte"] = filters["price_max"]
    if price_filter:
        filter_conditions.append({"price": price_filter})
    
    # Bedrooms filters
    bedrooms_filter = {}
    if "bedrooms_min" in filters and filters["bedrooms_min"] is not None:
        bedrooms_filter["$gte"] = filters["bedrooms_min"]
    if "bedrooms_max" in filters and filters["bedrooms_max"] is not None:
        bedrooms_filter["$lte"] = filters["bedrooms_max"]
    if bedrooms_filter:
        filter_conditions.append({"bedrooms": bedrooms_filter})
    
    # Bathrooms filters
    bathrooms_filter = {}
    if "bathrooms_min" in filters and filters["bathrooms_min"] is not None:
        bathrooms_filter["$gte"] = filters["bathrooms_min"]
    if "bathrooms_max" in filters and filters["bathrooms_max"] is not None:
        bathrooms_filter["$lte"] = filters["bathrooms_max"]
    if bathrooms_filter:
        filter_conditions.append({"bathrooms": bathrooms_filter})
    
    # Area sqft filters
    area_sqft_filter = {}
    if "area_sqft_min" in filters and filters["area_sqft_min"] is not None:
        area_sqft_filter["$gte"] = filters["area_sqft_min"]
    if "area_sqft_max" in filters and filters["area_sqft_max"] is not None:
        area_sqft_filter["$lte"] = filters["area_sqft_max"]
    if area_sqft_filter:
        filter_conditions.append({"area_sqft": area_sqft_filter})
    
    if filter_conditions:
        return {"$and": filter_conditions}
    return {}

async def _retrieve_points_from_qdrant(property_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Retrieve specific points from Qdrant by their MongoDB property IDs.
    
    Args:
        property_ids: List of MongoDB ObjectId strings
        
    Returns:
        Dictionary mapping property_id -> {vector, payload, qdrant_id}
    """
    import asyncio
    import requests
    from common.qdrant import PROPERTIES_COLLECTION
    from common.config import get_settings
    
    if not property_ids:
        return {}
    
    # Convert MongoDB IDs to Qdrant point IDs
    qdrant_point_ids = [_object_id_to_qdrant_id(prop_id) for prop_id in property_ids]
    
    # Create ID mapping for reverse lookup
    id_mapping = {qdrant_id: prop_id for qdrant_id, prop_id in zip(qdrant_point_ids, property_ids)}
    
    settings = get_settings()
    url = f"{settings.QDRANT_URL}/collections/{PROPERTIES_COLLECTION}/points"
    
    # Prepare headers
    headers = {"Content-Type": "application/json"}
    if hasattr(settings, 'QDRANT_API_KEY') and settings.QDRANT_API_KEY:
        headers["api-key"] = settings.QDRANT_API_KEY
    
    # Retrieve points by IDs
    payload = {
        "ids": qdrant_point_ids,
        "with_payload": True,
        "with_vectors": True,
    }
    
    def _retrieve():
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result_data = response.json()
        
        # Parse response
        points = []
        if isinstance(result_data, dict) and "result" in result_data:
            points = result_data["result"]
        elif isinstance(result_data, list):
            points = result_data
        
        return points
    
    loop = asyncio.get_event_loop()
    points = await loop.run_in_executor(None, _retrieve)
    
    # Map results back to MongoDB IDs
    result_map = {}
    for point in points:
        if isinstance(point, dict):
            qdrant_id = point.get("id")
            vector = point.get("vector")
            payload_data = point.get("payload", {})
        else:
            qdrant_id = getattr(point, 'id', None)
            vector = getattr(point, 'vector', None)
            payload_data = getattr(point, 'payload', {}) or {}
        
        if qdrant_id in id_mapping:
            prop_id = id_mapping[qdrant_id]
            result_map[prop_id] = {
                "vector": vector,
                "payload": payload_data,
                "qdrant_id": qdrant_id,
            }
    
    return result_map

def _calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors using pure Python."""
    if len(vec1) != len(vec2):
        return 0.0
    
    # Calculate dot product
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    
    # Calculate norms
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))

async def _filter_then_search_async(query: str, k: int = 10, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    FILTER-FIRST APPROACH: 
    1. Filter properties in MongoDB using extracted filters
    2. Retrieve those filtered properties from Qdrant
    3. Calculate similarity scores for filtered properties only
    4. Return top 10 (or less if fewer than 10 match)
    
    Args:
        query: Search query text
        k: Number of results to return (default 10)
        filters: Optional dictionary of filters (city, price_min, price_max, bedrooms, etc.)
        
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
        
        logger.info(f"[PROPERTY_SEARCH] Searching for: {query}")
        if filters:
            logger.info(f"[PROPERTY_SEARCH] Filters: {filters}")
        
        # Generate query embedding
        query_vec = embed_text(query)
        logger.info(f"[PROPERTY_SEARCH] Generated embedding, dimension: {len(query_vec)}")
        
        # Get database client and database
        client = get_database_client()
        db = client["proppal"]
        
        # STEP 1: Filter properties in MongoDB first
        mongo_filter = _build_mongo_filter(filters)
        
        if mongo_filter:
            logger.info(f"[PROPERTY_SEARCH] Applying MongoDB filter: {mongo_filter}")
            # Get IDs of properties that match the filter
            filtered_cursor = db["properties"].find(mongo_filter, {"_id": 1})
            filtered_docs = await filtered_cursor.to_list(length=1000)  # Limit to prevent memory issues
            filtered_property_ids = [str(doc["_id"]) for doc in filtered_docs]
            filter_count = len(filtered_property_ids)
            logger.info(f"[PROPERTY_SEARCH] MongoDB filter matched {filter_count} properties")
        else:
            # No filters - get all property IDs (limit to reasonable number)
            filtered_cursor = db["properties"].find({}, {"_id": 1}).limit(1000)
            filtered_docs = await filtered_cursor.to_list(length=1000)
            filtered_property_ids = [str(doc["_id"]) for doc in filtered_docs]
            filter_count = len(filtered_property_ids)
            logger.info(f"[PROPERTY_SEARCH] No filters applied, using {filter_count} properties")
        
        if not filtered_property_ids:
            logger.warning(f"[PROPERTY_SEARCH] No properties match the filters")
            return {
                "success": True,
                "query": query,
                "results": [],
                "count": 0,
                "filters_applied": filters if filters else {},
                "filter_matched_count": filter_count
            }
        
        # STEP 2: Retrieve filtered properties from Qdrant
        logger.info(f"[PROPERTY_SEARCH] Retrieving {len(filtered_property_ids)} properties from Qdrant")
        qdrant_points = await _retrieve_points_from_qdrant(filtered_property_ids)
        logger.info(f"[PROPERTY_SEARCH] Retrieved {len(qdrant_points)} points from Qdrant")
        
        if not qdrant_points:
            logger.warning(f"[PROPERTY_SEARCH] No points found in Qdrant for filtered properties")
            return {
                "success": True,
                "query": query,
                "results": [],
                "count": 0,
                "filters_applied": filters if filters else {},
                "filter_matched_count": filter_count
            }
        
        # STEP 3: Calculate similarity scores for filtered properties
        scored_properties = []
        for prop_id, point_data in qdrant_points.items():
            vector = point_data.get("vector")
            if vector:
                similarity = _calculate_cosine_similarity(query_vec, vector)
                scored_properties.append({
                    "id": prop_id,
                    "score": similarity,
                    "payload": point_data.get("payload", {}),
                })
        
        logger.info(f"[PROPERTY_SEARCH] Calculated similarity scores for {len(scored_properties)} properties")
        
        # STEP 4: Sort by similarity score (descending) and take top k
        scored_properties.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_results = scored_properties[:k]
        
        logger.info(f"[PROPERTY_SEARCH] Selected top {len(top_results)} results")
        
        if not top_results:
            return {
                "success": True,
                "query": query,
                "results": [],
                "count": 0,
                "filters_applied": filters if filters else {},
                "filter_matched_count": filter_count
            }
        
        # STEP 5: Fetch full property documents from MongoDB
        property_ids = [ObjectId(result["id"]) for result in top_results]
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
        
        # STEP 6: Combine MongoDB data with similarity scores
        score_map = {result["id"]: result["score"] for result in top_results}
        
        results = []
        for prop in properties:
            prop_id_str = str(prop["_id"])
            if prop_id_str in score_map:
                prop["_id"] = prop_id_str
                prop["score"] = score_map[prop_id_str]
                results.append(prop)
        
        # Sort by score (descending) to maintain order
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        logger.info(f"[PROPERTY_SEARCH] Returning {len(results)} results")
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results),
            "filters_applied": filters if filters else {},
            "filter_matched_count": filter_count
        }
        
    except Exception as e:
        logger.error(f"[PROPERTY_SEARCH] Error: {str(e)}")
        logger.error(f"[PROPERTY_SEARCH] Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": [],
            "count": 0,
            "filters_applied": filters if filters else {},
            "filter_matched_count": 0
        }
    finally:
        # Always close the database client
        if client:
            client.close()

def _run_async_search(search_coro):
    """Helper to run asyncio code from a sync context (safe in running loops)."""
    try:
        asyncio.get_running_loop()
        # Already in an async context, use thread pool
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, search_coro)
            return future.result()
    except RuntimeError:
        return asyncio.run(search_coro)
    except Exception as e:
        return {"success": False, "error": str(e), "results": [], "count": 0}

def _property_search_impl(query: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Internal implementation of property search using the filter-first approach.
    """
    search_coro = _filter_then_search_async(query, k=10, filters=filters)
    return _run_async_search(search_coro)

@tool
def property_search_tool(query: str) -> Dict[str, Any]:
    """
    Searches for properties based on a natural language query.
    Automatically extracts filters (city, area, price, bedrooms, property type, etc.) from the query.
    
    Flow:
    1. Extract filters from query
    2. Filter properties in MongoDB using extracted filters
    3. Retrieve filtered properties from Qdrant
    4. Calculate similarity scores for filtered properties only
    5. Return top 10 results (or less if fewer than 10 match)
    
    Args:
        query: The user's search query (e.g., "3 bedroom house in Islamabad under 1 crore").
    """
    # Extract filters from the query, but don't fail if extraction fails
    filters = None
    try:
        from .filter_extractor import extract_property_filters
        filters = extract_property_filters(query)
        if not filters:
            print(f"[DEBUG] No filters extracted from query: {query}")
    except Exception as e:
        # If filter extraction fails, continue without filters
        print(f"Property filter extraction failed (continuing without filters): {e}")
        filters = None
    
    return _property_search_impl(query, filters)
