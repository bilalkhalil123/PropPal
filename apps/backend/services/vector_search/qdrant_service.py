"""
Qdrant vector search service.

Stores and retrieves embeddings in Qdrant. Point IDs are derived from string IDs (UUID)
via _string_id_to_qdrant_id. Payloads store property_id, profile_id, or service_id as UUID
strings; the app fetches full rows from Postgres by that UUID after vector search.
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


def _string_id_to_qdrant_id(id_str: str) -> int:
    """
    Convert string ID (UUID) to Qdrant-compatible integer point ID.
    Uses hash for consistent mapping. App fetches full rows from Postgres by this UUID after vector search.
    """
    hash_obj = hashlib.sha256(id_str.encode("utf-8"))
    hash_bytes = hash_obj.digest()[:8]
    point_id = int.from_bytes(hash_bytes, byteorder="big")
    return point_id % (2**63 - 1)


async def recreate_properties_collection() -> None:
    """
    Delete and re-create the properties collection in Qdrant.
    Ensures a fresh start for 100% data consistency.
    """
    import asyncio
    from qdrant_client.models import Distance, VectorParams
    from common.qdrant import VECTOR_DIMENSION

    client = get_qdrant_client()
    loop = asyncio.get_event_loop()

    print(f"[QDRANT] Resetting collection: {PROPERTIES_COLLECTION}")
    
    # Delete if exists
    try:
        await loop.run_in_executor(
            None,
            lambda: client.delete_collection(PROPERTIES_COLLECTION)
        )
    except Exception:
        pass

    # Re-create
    await loop.run_in_executor(
        None,
        lambda: client.create_collection(
            collection_name=PROPERTIES_COLLECTION,
            vectors_config=VectorParams(
                size=VECTOR_DIMENSION,
                distance=Distance.COSINE,
            ),
        )
    )
    print(f"[QDRANT] Collection '{PROPERTIES_COLLECTION}' re-created successfully.")


async def upsert_property_embedding(
    property_id: str,
    embedding: List[float],
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Store or update a property embedding in Qdrant.
    
    Args:
        property_id: Property UUID string (Postgres). Stored in payload for lookup; app fetches full row from Postgres by this ID.
        embedding: Vector embedding (384 dimensions)
        metadata: Optional metadata to store with the vector
    """
    import asyncio
    
    client = get_qdrant_client()
    
    payload = metadata or {}
    payload["property_id"] = property_id  # UUID string for Postgres lookup after vector search
    
    qdrant_point_id = _string_id_to_qdrant_id(property_id)
    
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


async def upsert_property_embeddings_batch(
    items: List[tuple],
) -> None:
    """
    Upsert multiple property embeddings in one Qdrant request.
    Each item is (property_id: str, embedding: List[float], metadata: Optional[Dict]).
    Reduces HTTP calls and avoids read timeouts on large backfills.
    """
    import asyncio

    if not items:
        return
    client = get_qdrant_client()
    points = []
    for property_id, embedding, metadata in items:
        payload = dict(metadata or {})
        payload["property_id"] = property_id
        points.append(
            PointStruct(
                id=_string_id_to_qdrant_id(property_id),
                vector=embedding,
                payload=payload,
            )
        )
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: client.upsert(collection_name=PROPERTIES_COLLECTION, points=points),
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
        filters: Optional filters. Supports:
            - city: str — exact match on city payload field
            - price_min / price_max: float — range filter on price
            - geo_center: {"lat": float, "lon": float} — center for geo filter
            - geo_radius_m: float — radius in meters for geo filter
        
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
    
    # Build geo_radius filter dict (handled separately for direct HTTP API)
    geo_filter_dict = None
    if filters and "geo_center" in filters and "geo_radius_m" in filters:
        geo_center = filters["geo_center"]
        geo_filter_dict = {
            "key": "location",
            "geo_radius": {
                "center": {
                    "lat": float(geo_center["lat"]),
                    "lon": float(geo_center["lon"]),
                },
                "radius": float(filters["geo_radius_m"]),
            },
        }

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
        filter_dict = {}
        if qdrant_filter:
            try:
                if hasattr(qdrant_filter, 'model_dump'):
                    filter_dict = qdrant_filter.model_dump(exclude_none=True)
                elif hasattr(qdrant_filter, 'dict'):
                    filter_dict = qdrant_filter.dict(exclude_none=True)
                else:
                    # Manual serialization
                    if hasattr(qdrant_filter, 'must') and qdrant_filter.must:
                        filter_dict["must"] = []
                        for condition in qdrant_filter.must:
                            if hasattr(condition, 'key') and hasattr(condition, 'match'):
                                match_value = condition.match.value if hasattr(condition.match, 'value') else condition.match
                                filter_dict["must"].append({
                                    "key": condition.key,
                                    "match": {"value": match_value}
                                })
            except Exception as e:
                print(f"[WARNING] Failed to serialize filter: {e}, continuing without filter")

        # Merge geo_radius filter into the filter dict
        if geo_filter_dict:
            if "must" not in filter_dict:
                filter_dict["must"] = []
            filter_dict["must"].append(geo_filter_dict)

        if filter_dict:
            payload["filter"] = filter_dict
        
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
            
            # UUID string from payload for Postgres lookup
            prop_id = payload.get("property_id") if payload else None
            if not prop_id and point_id:
                prop_id = str(point_id)
            
            if prop_id:
                formatted_results.append({
                    "id": prop_id,
                    "score": score,
                    "payload": payload,
                })
        else:
            # Fallback for object format
            point_id = getattr(point, 'id', None)
            point_payload = getattr(point, 'payload', {}) or {}
            point_score = getattr(point, 'score', 1.0)
            prop_id = point_payload.get("property_id") if point_payload else None
            if not prop_id and point_id:
                prop_id = str(point_id)
            if prop_id:
                formatted_results.append({
                    "id": prop_id,
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
        profile_id: Builder profile UUID string (Postgres). Stored in payload; app fetches full row from Postgres by this ID.
        embedding: Vector embedding (384 dimensions)
        metadata: Optional metadata to store with the vector
    """
    import asyncio
    
    client = get_qdrant_client()
    
    payload = metadata or {}
    payload["profile_id"] = profile_id  # UUID string for Postgres lookup (builder profile by ID)
    
    qdrant_point_id = _string_id_to_qdrant_id(profile_id)
    
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


async def upsert_builder_profile_embeddings_batch(
    items: List[tuple],
) -> None:
    """
    Upsert multiple builder profile embeddings in one Qdrant request.
    Each item is (profile_id: str, embedding: List[float], metadata: Optional[Dict]).
    """
    import asyncio

    if not items:
        return
    client = get_qdrant_client()
    points = []
    for profile_id, embedding, metadata in items:
        payload = dict(metadata or {})
        payload["profile_id"] = profile_id
        points.append(
            PointStruct(
                id=_string_id_to_qdrant_id(profile_id),
                vector=embedding,
                payload=payload,
            )
        )
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: client.upsert(collection_name=BUILDER_PROFILES_COLLECTION, points=points),
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
            profile_id = payload.get("profile_id") if payload else None
            if not profile_id and point_id:
                profile_id = str(point_id)
            if profile_id:
                formatted_results.append({
                    "id": profile_id,
                    "score": score,
                    "payload": payload,
                })
        else:
            point_id = getattr(point, 'id', None)
            point_payload = getattr(point, 'payload', {}) or {}
            point_score = getattr(point, 'score', 1.0)
            profile_id = point_payload.get("profile_id") if point_payload else None
            if not profile_id and point_id:
                profile_id = str(point_id)
            if profile_id:
                formatted_results.append({
                    "id": profile_id,
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
        service_id: Builder service UUID string (Postgres). Stored in payload; app fetches full row from Postgres by this ID.
        embedding: Vector embedding (384 dimensions)
        metadata: Optional metadata to store with the vector
    """
    import asyncio
    
    client = get_qdrant_client()
    
    payload = metadata or {}
    payload["service_id"] = service_id  # UUID string for Postgres lookup (builder service by ID)
    
    qdrant_point_id = _string_id_to_qdrant_id(service_id)
    
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


async def upsert_builder_service_embeddings_batch(
    items: List[tuple],
) -> None:
    """
    Upsert multiple builder service embeddings in one Qdrant request.
    Each item is (service_id: str, embedding: List[float], metadata: Optional[Dict]).
    """
    import asyncio

    if not items:
        return
    client = get_qdrant_client()
    points = []
    for service_id, embedding, metadata in items:
        payload = dict(metadata or {})
        payload["service_id"] = service_id
        points.append(
            PointStruct(
                id=_string_id_to_qdrant_id(service_id),
                vector=embedding,
                payload=payload,
            )
        )
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: client.upsert(collection_name=BUILDER_SERVICES_COLLECTION, points=points),
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
            service_id = payload.get("service_id") if payload else None
            if not service_id and point_id:
                service_id = str(point_id)
            if service_id:
                formatted_results.append({
                    "id": service_id,
                    "score": score,
                    "payload": payload,
                })
        else:
            point_id = getattr(point, 'id', None)
            point_payload = getattr(point, 'payload', {}) or {}
            point_score = getattr(point, 'score', 1.0)
            service_id = point_payload.get("service_id") if point_payload else None
            if not service_id and point_id:
                service_id = str(point_id)
            if service_id:
                formatted_results.append({
                    "id": service_id,
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
        point_id: UUID string (property_id / profile_id / service_id); converted to Qdrant integer point ID.
    """
    import asyncio
    
    client = get_qdrant_client()
    
    qdrant_point_id = _string_id_to_qdrant_id(point_id)
    
    # Qdrant client is synchronous, run in thread pool for async compatibility
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: client.delete(collection_name=collection_name, points_selector=[qdrant_point_id])
    )

