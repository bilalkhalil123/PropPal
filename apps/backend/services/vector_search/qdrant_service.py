"""
Qdrant vector search service.

This service provides functions to store and retrieve embeddings from Qdrant,
replacing MongoDB Atlas Vector Search.
"""

import hashlib
from typing import Any, Dict, List, Optional
from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct

from common.qdrant import (
    get_qdrant_client,
    PROPERTIES_COLLECTION,
    BUILDER_PROFILES_COLLECTION,
    BUILDER_SERVICES_COLLECTION,
)
from common.config import get_settings


def _object_id_to_qdrant_id(object_id_str: str) -> int:
    """
    Convert MongoDB ObjectId string to Qdrant-compatible integer ID.
    
    Uses hash function to convert ObjectId string to unsigned integer.
    This ensures consistent mapping between MongoDB IDs and Qdrant point IDs.
    
    Args:
        object_id_str: MongoDB ObjectId as string
        
    Returns:
        Unsigned integer suitable for Qdrant point ID
    """
    # Use SHA256 hash and take first 8 bytes to create a 64-bit integer
    hash_obj = hashlib.sha256(object_id_str.encode('utf-8'))
    hash_bytes = hash_obj.digest()[:8]
    # Convert to unsigned integer (max 2^64 - 1)
    point_id = int.from_bytes(hash_bytes, byteorder='big')
    # Ensure it's within Qdrant's acceptable range (0 to 2^63 - 1 for signed, but we use unsigned)
    # Qdrant accepts up to 2^63 - 1, so we'll use modulo to ensure it fits
    return point_id % (2**63 - 1)


async def upsert_property_embedding(
    property_id: str,
    embedding: List[float],
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Store or update a property embedding in Qdrant.
    
    Args:
        property_id: MongoDB property ObjectId as string
        embedding: Vector embedding (384 dimensions)
        metadata: Optional metadata to store with the vector
    """
    import asyncio
    
    client = get_qdrant_client()
    
    payload = metadata or {}
    payload["property_id"] = property_id  # Store original MongoDB ID in payload
    
    # Convert ObjectId string to Qdrant-compatible integer ID
    qdrant_point_id = _object_id_to_qdrant_id(property_id)
    
    # Qdrant client is synchronous, run in thread pool for async compatibility
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: client.upsert(
            collection_name=PROPERTIES_COLLECTION,
            points=[
                PointStruct(
                    id=qdrant_point_id,
                    vector=embedding,
                    payload=payload,
                )
            ],
        )
    )


async def search_properties(
    query_vector: List[float],
    limit: int = 10,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Search properties using vector similarity.
    
    Args:
        query_vector: Query embedding vector
        limit: Number of results to return
        filters: Optional filters (e.g., {"city": "Lahore"})
        
    Returns:
        List of search results with scores and property IDs
    """
    import asyncio
    
    client = get_qdrant_client()
    
    qdrant_filter = None
    if filters:
        conditions = []
        if "city" in filters:
            conditions.append(
                FieldCondition(key="city", match=MatchValue(value=filters["city"]))
            )
        if "price_min" in filters or "price_max" in filters:
            price_conditions = {}
            if "price_min" in filters:
                price_conditions["gte"] = float(filters["price_min"])
            if "price_max" in filters:
                price_conditions["lte"] = float(filters["price_max"])
            if price_conditions:
                conditions.append(
                    FieldCondition(key="price", range=price_conditions)
                )
        
        if conditions:
            qdrant_filter = Filter(must=conditions)
    
    # Qdrant client is synchronous, run in thread pool for async compatibility
    loop = asyncio.get_event_loop()
    
    # Use the new /points/query API (search is deprecated)
    def _search():
        # Make direct HTTP request to /collections/{name}/points/query endpoint
        import requests
        
        settings = get_settings()
        url = f"{settings.QDRANT_URL}/collections/{PROPERTIES_COLLECTION}/points/query"
        
        # Build request payload
        payload = {
            "query": query_vector,  # Direct vector query
            "limit": limit,
            "with_payload": True,
        }
        
        # Add filter if provided - convert Filter object to dict for JSON
        if qdrant_filter:
            # Convert Filter object to dictionary for JSON serialization
            try:
                if hasattr(qdrant_filter, 'model_dump'):
                    payload["filter"] = qdrant_filter.model_dump(exclude_none=True)
                elif hasattr(qdrant_filter, 'dict'):
                    payload["filter"] = qdrant_filter.dict(exclude_none=True)
                else:
                    # Manual serialization
                    filter_dict = {}
                    if hasattr(qdrant_filter, 'must') and qdrant_filter.must:
                        filter_dict["must"] = []
                        for condition in qdrant_filter.must:
                            if hasattr(condition, 'key') and hasattr(condition, 'match'):
                                match_value = condition.match.value if hasattr(condition.match, 'value') else condition.match
                                filter_dict["must"].append({
                                    "key": condition.key,
                                    "match": {"value": match_value}
                                })
                    if filter_dict:
                        payload["filter"] = filter_dict
            except Exception as e:
                print(f"[WARNING] Failed to serialize filter: {e}, continuing without filter")
        
        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if hasattr(settings, 'QDRANT_API_KEY') and settings.QDRANT_API_KEY:
            headers["api-key"] = settings.QDRANT_API_KEY
        
        # Make POST request
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        # Parse response
        result_data = response.json()
        
        # Parse response - result contains a dict with 'points' key
        if isinstance(result_data, dict) and "result" in result_data:
            results = result_data["result"]
            if isinstance(results, dict) and "points" in results:
                return results["points"]
            elif isinstance(results, list):
                return results
        elif isinstance(result_data, list):
            return result_data
        return []
    
    results = await loop.run_in_executor(None, _search)
    
    # Parse results - they come as dictionaries from HTTP response
    formatted_results = []
    for point in results:
        if isinstance(point, dict):
            # Result is a dictionary from HTTP response
            point_id = point.get("id")
            payload = point.get("payload", {})
            score = point.get("score", 1.0)
            
            # Get MongoDB ObjectId from payload
            mongo_id = payload.get("property_id") if payload else None
            if not mongo_id and point_id:
                mongo_id = str(point_id)
            
            if mongo_id:  # Only add if we have an ID
                formatted_results.append({
                    "id": mongo_id,
                    "score": score,
                    "payload": payload,
                })
        else:
            # Fallback for object format
            point_id = getattr(point, 'id', None)
            point_payload = getattr(point, 'payload', {}) or {}
            point_score = getattr(point, 'score', 1.0)
            mongo_id = point_payload.get("property_id") if point_payload else None
            if not mongo_id and point_id:
                mongo_id = str(point_id)
            if mongo_id:
                formatted_results.append({
                    "id": mongo_id,
                    "score": point_score,
                    "payload": point_payload,
                })
    
    return formatted_results


async def upsert_builder_profile_embedding(
    profile_id: str,
    embedding: List[float],
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Store or update a builder profile embedding in Qdrant.
    
    Args:
        profile_id: MongoDB builder profile ObjectId as string
        embedding: Vector embedding (384 dimensions)
        metadata: Optional metadata to store with the vector
    """
    import asyncio
    
    client = get_qdrant_client()
    
    payload = metadata or {}
    payload["profile_id"] = profile_id  # Store original MongoDB ID in payload
    
    # Convert ObjectId string to Qdrant-compatible integer ID
    qdrant_point_id = _object_id_to_qdrant_id(profile_id)
    
    # Qdrant client is synchronous, run in thread pool for async compatibility
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: client.upsert(
            collection_name=BUILDER_PROFILES_COLLECTION,
            points=[
                PointStruct(
                    id=qdrant_point_id,
                    vector=embedding,
                    payload=payload,
                )
            ],
        )
    )


async def search_builder_profiles(
    query_vector: List[float],
    limit: int = 10,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Search builder profiles using vector similarity.
    
    Args:
        query_vector: Query embedding vector
        limit: Number of results to return
        filters: Optional filters (e.g., {"city": "Lahore"})
        
    Returns:
        List of search results with scores and profile IDs
    """
    import asyncio
    
    client = get_qdrant_client()
    
    qdrant_filter = None
    if filters:
        conditions = []
        if "city" in filters:
            # City is stored directly in payload, not nested
            conditions.append(
                FieldCondition(
                    key="city",
                    match=MatchValue(value=filters["city"])
                )
            )
        
        if conditions:
            qdrant_filter = Filter(must=conditions)
    
    # Qdrant client is synchronous, run in thread pool for async compatibility
    loop = asyncio.get_event_loop()
    
    def _search():
        import requests
        settings = get_settings()
        url = f"{settings.QDRANT_URL}/collections/{BUILDER_PROFILES_COLLECTION}/points/query"
        payload = {
            "query": query_vector,
            "limit": limit,
            "with_payload": True,
        }
        # Add filter if provided - convert Filter object to dict for JSON
        if qdrant_filter:
            try:
                if hasattr(qdrant_filter, 'model_dump'):
                    filter_dict = qdrant_filter.model_dump(exclude_none=True)
                elif hasattr(qdrant_filter, 'dict'):
                    filter_dict = qdrant_filter.dict(exclude_none=True)
                else:
                    # Manual serialization for nested structures
                    filter_dict = {}
                    if hasattr(qdrant_filter, 'must') and qdrant_filter.must:
                        filter_dict["must"] = []
                        for condition in qdrant_filter.must:
                            if hasattr(condition, 'key') and hasattr(condition, 'match'):
                                match_value = condition.match.value if hasattr(condition.match, 'value') else condition.match
                                filter_dict["must"].append({
                                    "key": condition.key,
                                    "match": {"value": match_value}
                                })
                if filter_dict:
                    payload["filter"] = filter_dict
            except Exception as e:
                print(f"[WARNING] Failed to serialize filter: {e}, continuing without filter")
        headers = {"Content-Type": "application/json"}
        if hasattr(settings, 'QDRANT_API_KEY') and settings.QDRANT_API_KEY:
            headers["api-key"] = settings.QDRANT_API_KEY
        response = requests.post(url, json=payload, headers=headers)
        if not response.ok:
            print(f"[DEBUG] Qdrant error response: {response.status_code}")
            print(f"[DEBUG] Response body: {response.text}")
            print(f"[DEBUG] Request payload keys: {list(payload.keys())}")
            if "filter" in payload:
                print(f"[DEBUG] Filter structure: {payload['filter']}")
        response.raise_for_status()
        result_data = response.json()
        # Parse response - result contains a dict with 'points' key
        if isinstance(result_data, dict) and "result" in result_data:
            results = result_data["result"]
            if isinstance(results, dict) and "points" in results:
                return results["points"]
            elif isinstance(results, list):
                return results
        elif isinstance(result_data, list):
            return result_data
        return []
    
    results = await loop.run_in_executor(None, _search)
    
    # Parse results - they come as dictionaries from HTTP response
    formatted_results = []
    for point in results:
        if isinstance(point, dict):
            point_id = point.get("id")
            payload = point.get("payload", {})
            score = point.get("score", 1.0)
            mongo_id = payload.get("profile_id") if payload else None
            if not mongo_id and point_id:
                mongo_id = str(point_id)
            if mongo_id:
                formatted_results.append({
                    "id": mongo_id,
                    "score": score,
                    "payload": payload,
                })
        else:
            point_id = getattr(point, 'id', None)
            point_payload = getattr(point, 'payload', {}) or {}
            point_score = getattr(point, 'score', 1.0)
            mongo_id = point_payload.get("profile_id") if point_payload else None
            if not mongo_id and point_id:
                mongo_id = str(point_id)
            if mongo_id:
                formatted_results.append({
                    "id": mongo_id,
                    "score": point_score,
                    "payload": point_payload,
                })
    return formatted_results


async def upsert_builder_service_embedding(
    service_id: str,
    embedding: List[float],
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Store or update a builder service embedding in Qdrant.
    
    Args:
        service_id: MongoDB builder service ObjectId as string
        embedding: Vector embedding (384 dimensions)
        metadata: Optional metadata to store with the vector
    """
    import asyncio
    
    client = get_qdrant_client()
    
    payload = metadata or {}
    payload["service_id"] = service_id  # Store original MongoDB ID in payload
    
    # Convert ObjectId string to Qdrant-compatible integer ID
    qdrant_point_id = _object_id_to_qdrant_id(service_id)
    
    # Qdrant client is synchronous, run in thread pool for async compatibility
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: client.upsert(
            collection_name=BUILDER_SERVICES_COLLECTION,
            points=[
                PointStruct(
                    id=qdrant_point_id,
                    vector=embedding,
                    payload=payload,
                )
            ],
        )
    )


async def search_builder_services(
    query_vector: List[float],
    limit: int = 10,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Search builder services using vector similarity.
    
    Args:
        query_vector: Query embedding vector
        limit: Number of results to return
        filters: Optional filters
        
    Returns:
        List of search results with scores and service IDs
    """
    import asyncio
    
    client = get_qdrant_client()
    
    qdrant_filter = None
    if filters:
        conditions = []
        for key, value in filters.items():
            conditions.append(
                FieldCondition(key=key, match=MatchValue(value=value))
            )
        
        if conditions:
            qdrant_filter = Filter(must=conditions)
    
    # Qdrant client is synchronous, run in thread pool for async compatibility
    loop = asyncio.get_event_loop()
    
    def _search():
        import requests
        settings = get_settings()
        url = f"{settings.QDRANT_URL}/collections/{BUILDER_SERVICES_COLLECTION}/points/query"
        payload = {
            "query": query_vector,
            "limit": limit,
            "with_payload": True,
        }
        # Add filter if provided - convert Filter object to dict for JSON
        if qdrant_filter:
            try:
                if hasattr(qdrant_filter, 'model_dump'):
                    payload["filter"] = qdrant_filter.model_dump(exclude_none=True)
                elif hasattr(qdrant_filter, 'dict'):
                    payload["filter"] = qdrant_filter.dict(exclude_none=True)
            except Exception:
                pass  # Skip filter if serialization fails
        headers = {"Content-Type": "application/json"}
        if hasattr(settings, 'QDRANT_API_KEY') and settings.QDRANT_API_KEY:
            headers["api-key"] = settings.QDRANT_API_KEY
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result_data = response.json()
        # Parse response - result contains a dict with 'points' key
        if isinstance(result_data, dict) and "result" in result_data:
            results = result_data["result"]
            if isinstance(results, dict) and "points" in results:
                return results["points"]
            elif isinstance(results, list):
                return results
        elif isinstance(result_data, list):
            return result_data
        return []
    
    results = await loop.run_in_executor(None, _search)
    
    # Parse results - they come as dictionaries from HTTP response
    formatted_results = []
    for point in results:
        if isinstance(point, dict):
            point_id = point.get("id")
            payload = point.get("payload", {})
            score = point.get("score", 1.0)
            mongo_id = payload.get("service_id") if payload else None
            if not mongo_id and point_id:
                mongo_id = str(point_id)
            if mongo_id:
                formatted_results.append({
                    "id": mongo_id,
                    "score": score,
                    "payload": payload,
                })
        else:
            point_id = getattr(point, 'id', None)
            point_payload = getattr(point, 'payload', {}) or {}
            point_score = getattr(point, 'score', 1.0)
            mongo_id = point_payload.get("service_id") if point_payload else None
            if not mongo_id and point_id:
                mongo_id = str(point_id)
            if mongo_id:
                formatted_results.append({
                    "id": mongo_id,
                    "score": point_score,
                    "payload": point_payload,
                })
    return formatted_results


async def delete_embedding(
    collection_name: str,
    point_id: str,
) -> None:
    """
    Delete an embedding from Qdrant.
    
    Args:
        collection_name: Qdrant collection name
        point_id: Point ID to delete
    """
    client = get_qdrant_client()
    client.delete(collection_name=collection_name, points_selector=[point_id])

