"""
Property search tool for the Listing Agent.

Uses a hybrid approach: filter first in Postgres, then retrieve filtered properties from Qdrant
and apply similarity search only on those filtered properties. IDs are UUID strings.
"""
import asyncio
import concurrent.futures
import traceback
import hashlib
import math
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool

from common.db import get_db_session_ctx
from common.repositories.property_repository import PropertyRepository
from services.embeddings.service import embed_text


def _string_id_to_qdrant_id(id_str: str) -> int:
    """Convert UUID (or any string ID) to Qdrant-compatible integer ID."""
    hash_obj = hashlib.sha256(id_str.encode("utf-8"))
    hash_bytes = hash_obj.digest()[:8]
    return int.from_bytes(hash_bytes, byteorder="big") % (2**63 - 1)


def _filters_to_list_ids_params(filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Map filter dict from extractor to PropertyRepository.list_ids_with_filters kwargs."""
    if not filters or not isinstance(filters, dict) or len(filters) == 0:
        return {"limit": 1000}
    params: Dict[str, Any] = {"limit": 1000}
    if filters.get("city"):
        params["city"] = filters["city"].strip()
    if filters.get("area"):
        params["area"] = filters["area"].strip()
    if filters.get("property_type"):
        params["property_type"] = filters["property_type"].strip().lower()
    if filters.get("price_min") is not None:
        params["price_min"] = filters["price_min"]
    if filters.get("price_max") is not None:
        params["price_max"] = filters["price_max"]
    if filters.get("bedrooms_min") is not None:
        params["bedrooms_min"] = filters["bedrooms_min"]
    if filters.get("bedrooms_max") is not None:
        params["bedrooms_max"] = filters["bedrooms_max"]
    if filters.get("bathrooms_min") is not None:
        params["bathrooms_min"] = filters["bathrooms_min"]
    if filters.get("bathrooms_max") is not None:
        params["bathrooms_max"] = filters["bathrooms_max"]
    if filters.get("area_sqft_min") is not None:
        params["area_sqft_min"] = filters["area_sqft_min"]
    if filters.get("area_sqft_max") is not None:
        params["area_sqft_max"] = filters["area_sqft_max"]
    if filters.get("bedrooms") is not None:
        params["bedrooms"] = filters["bedrooms"]
    return params


async def _retrieve_points_from_qdrant(property_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Retrieve specific points from Qdrant by property IDs (UUID strings)."""
    import asyncio
    import requests
    from common.qdrant import PROPERTIES_COLLECTION
    from common.config import get_settings

    if not property_ids:
        return {}
    qdrant_point_ids = [_string_id_to_qdrant_id(pid) for pid in property_ids]
    id_mapping = {qdrant_id: prop_id for qdrant_id, prop_id in zip(qdrant_point_ids, property_ids)}
    settings = get_settings()
    url = f"{settings.QDRANT_URL}/collections/{PROPERTIES_COLLECTION}/points"
    headers = {"Content-Type": "application/json"}
    if getattr(settings, "QDRANT_API_KEY", None):
        headers["api-key"] = settings.QDRANT_API_KEY
    payload = {"ids": qdrant_point_ids, "with_payload": True, "with_vectors": True}

    def _retrieve():
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result_data = response.json()
        points = result_data.get("result", []) if isinstance(result_data, dict) else (result_data if isinstance(result_data, list) else [])
        return points

    loop = asyncio.get_event_loop()
    points = await loop.run_in_executor(None, _retrieve)
    result_map = {}
    for point in points:
        if isinstance(point, dict):
            qdrant_id = point.get("id")
            vector = point.get("vector")
            payload_data = point.get("payload", {})
        else:
            qdrant_id = getattr(point, "id", None)
            vector = getattr(point, "vector", None)
            payload_data = getattr(point, "payload", {}) or {}
        if qdrant_id in id_mapping:
            prop_id = id_mapping[qdrant_id]
            result_map[prop_id] = {"vector": vector, "payload": payload_data, "qdrant_id": qdrant_id}
    return result_map


def _calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    if len(vec1) != len(vec2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(dot_product / (norm1 * norm2))


# Top N properties to return (for cards); keep small to stay under LLM token limits
PROPERTY_SEARCH_TOP_K = 8


async def _filter_then_search_async(query: str, k: int = PROPERTY_SEARCH_TOP_K, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Filter properties in Postgres, retrieve from Qdrant, score, fetch full rows from Postgres."""
    import logging
    logger = logging.getLogger(__name__)
    filter_count = 0
    try:
        if not query:
            return {"success": True, "query": query, "results": [], "count": 0}
        logger.info(f"[PROPERTY_SEARCH] Searching for: {query}")
        if filters:
            logger.info(f"[PROPERTY_SEARCH] Filters: {filters}")
        query_vec = embed_text(query)
        logger.info(f"[PROPERTY_SEARCH] Generated embedding, dimension: {len(query_vec)}")

        async with get_db_session_ctx() as session:
            repo = PropertyRepository(session)
            params = _filters_to_list_ids_params(filters)
            filtered_property_ids = await repo.list_ids_with_filters(**params)
            filter_count = len(filtered_property_ids)
            logger.info(f"[PROPERTY_SEARCH] Postgres filter matched {filter_count} properties")

            if not filtered_property_ids:
                return {
                    "success": True,
                    "query": query,
                    "results": [],
                    "count": 0,
                    "filters_applied": filters or {},
                    "filter_matched_count": filter_count,
                }

            logger.info(f"[PROPERTY_SEARCH] Retrieving {len(filtered_property_ids)} properties from Qdrant")
            qdrant_points = await _retrieve_points_from_qdrant(filtered_property_ids)
            logger.info(f"[PROPERTY_SEARCH] Retrieved {len(qdrant_points)} points from Qdrant")

            if not qdrant_points:
                return {
                    "success": True,
                    "query": query,
                    "results": [],
                    "count": 0,
                    "filters_applied": filters or {},
                    "filter_matched_count": filter_count,
                }

            scored_properties = []
            for prop_id, point_data in qdrant_points.items():
                vector = point_data.get("vector")
                if vector:
                    similarity = _calculate_cosine_similarity(query_vec, vector)
                    scored_properties.append({"id": prop_id, "score": similarity, "payload": point_data.get("payload", {})})
            scored_properties.sort(key=lambda x: x.get("score", 0), reverse=True)
            top_results = scored_properties[:k]

            if not top_results:
                return {
                    "success": True,
                    "query": query,
                    "results": [],
                    "count": 0,
                    "filters_applied": filters or {},
                    "filter_matched_count": filter_count,
                }

            property_ids = [r["id"] for r in top_results]
            properties = await repo.list_by_ids(property_ids)
            logger.info(f"[PROPERTY_SEARCH] Fetched {len(properties)} properties from Postgres")
            score_map = {r["id"]: r["score"] for r in top_results}
            results = []
            for prop in properties:
                pid = prop.get("id") or prop.get("_id")
                if pid in score_map:
                    prop["score"] = score_map[pid]
                    prop["_id"] = pid
                    results.append(prop)
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
            logger.info(f"[PROPERTY_SEARCH] Returning {len(results)} results")
            # Short summary for the LLM to avoid token limit (413); full results go in state for API/cards
            summary_lines = []
            for i, p in enumerate(results[:k], 1):
                title = (p.get("title") or p.get("property_title") or "Property")[:50]
                price = p.get("price") or p.get("price_display") or "Price on request"
                city = (p.get("city") or p.get("location", {}).get("city") or "")[:30]
                summary_lines.append(f"{i}. {title} - {price} - {city}")
            summary_for_llm = "Found {} properties:\n".format(len(results)) + "\n".join(summary_lines) if results else "No properties found."
            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results),
                "filters_applied": filters or {},
                "filter_matched_count": filter_count,
                "summary_for_llm": summary_for_llm,
            }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[PROPERTY_SEARCH] Error: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": [],
            "count": 0,
            "filters_applied": filters or {},
            "filter_matched_count": 0,
            "summary_for_llm": f"Property search failed: {e}. Please try again.",
        }


def _run_async_search(search_coro):
    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, search_coro)
            return future.result()
    except RuntimeError:
        return asyncio.run(search_coro)
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "results": [],
            "count": 0,
            "summary_for_llm": f"Property search failed: {e}. Please try again.",
        }


def _property_search_impl(query: str, filters: Optional[Dict[str, Any]] = None) -> str:
    """Returns JSON string so ToolMessage content is valid JSON; agent will use summary_for_llm for LLM context."""
    import json
    search_coro = _filter_then_search_async(query, k=PROPERTY_SEARCH_TOP_K, filters=filters)
    result = _run_async_search(search_coro)
    return json.dumps(result, default=str)


@tool
def property_search_tool(query: str) -> str:
    """
    Searches for properties based on a natural language query.
    Extracts filters (city, area, price, bedrooms, property type, etc.) from the query.
    Returns top 8 properties. Flow: extract filters -> filter in Postgres -> Qdrant similarity -> return top 8 from Postgres.
    """
    filters = None
    try:
        from .filter_extractor import extract_property_filters
        filters = extract_property_filters(query)
    except Exception as e:
        print(f"Property filter extraction failed (continuing without filters): {e}")
    return _property_search_impl(query, filters)
