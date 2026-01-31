"""
Property recommendation service based on user's chat history.
Uses PostgreSQL (ChatHistoryRepository, PropertyRepository); IDs are UUID strings.
"""
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta

from services.embeddings.service import embed_text
from services.vector_search.qdrant_service import search_properties as qdrant_search_properties


async def get_recommended_properties(
    user_id: str,
    chat_repo: "ChatHistoryRepository",
    property_repo: "PropertyRepository",
    limit: int = 12,
    days_back: int = 30,
) -> Dict[str, Any]:
    """
    Generate property recommendations based on user's chat history.
    user_id: UUID string. Repos: Postgres ChatHistoryRepository and PropertyRepository.
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        docs = await chat_repo.list_by_user_id(user_id)
        docs = [d for d in docs if d.get("updated_at") and d["updated_at"] >= cutoff_date]
        docs.sort(key=lambda d: d.get("updated_at") or datetime.min, reverse=True)
        docs = docs[:20]

        if not docs:
            return await get_popular_properties(property_repo, limit)

        search_data = _extract_search_data(docs, days_back)

        if not search_data["queries"] and not search_data["property_ids"]:
            return await get_popular_properties(property_repo, limit)

        recommendations = await _generate_recommendations(
            search_data,
            property_repo,
            limit,
        )

        if recommendations["count"] > 0:
            return {**recommendations, "source": "recent_searches"}
        return await get_popular_properties(property_repo, limit)
    except Exception as e:
        print(f"[RECOMMENDATIONS] Error generating recommendations: {e}")
        return await get_popular_properties(property_repo, limit)


def _extract_search_data(
    docs: List[Dict[str, Any]],
    days_back: int = 30,
) -> Dict[str, Any]:
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)
    queries: List[Dict[str, Any]] = []
    property_ids: Set[str] = set()
    cities: Set[str] = set()
    property_types: Set[str] = set()

    for doc in docs:
        messages = doc.get("messages", [])
        for i in range(len(messages)):
            msg = messages[i]
            if msg.get("role") != "user":
                continue
            timestamp = msg.get("timestamp")
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except Exception:
                    continue
            if timestamp and timestamp < cutoff_date:
                continue
            if i + 1 < len(messages):
                ai_response = messages[i + 1]
                payload = ai_response.get("_payload", {})
                if payload.get("classification") == "listing_agent":
                    query_text = msg.get("content", "").strip()
                    if query_text:
                        queries.append({"query": query_text, "timestamp": timestamp or datetime.utcnow()})
                    for prop in payload.get("properties", []):
                        prop_id = prop.get("_id") or prop.get("id")
                        if prop_id:
                            property_ids.add(str(prop_id))
                        if prop.get("city"):
                            cities.add(prop["city"])
                        if prop.get("property_type"):
                            property_types.add(prop["property_type"])

    queries.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)
    return {
        "queries": queries[:10],
        "property_ids": list(property_ids),
        "cities": list(cities),
        "property_types": list(property_types),
    }


async def _generate_recommendations(
    search_data: Dict[str, Any],
    property_repo: "PropertyRepository",
    limit: int,
) -> Dict[str, Any]:
    queries = search_data["queries"]
    seen_property_ids = set(search_data["property_ids"])

    if not queries:
        return {"properties": [], "count": 0}

    recent_queries = queries[:3]

    if seen_property_ids:
        prop_ids = list(seen_property_ids)[:limit]
        direct_properties = await property_repo.list_by_ids(prop_ids)
        if len(direct_properties) >= limit:
            return {"properties": direct_properties[:limit], "count": len(direct_properties[:limit])}

    all_results: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set(seen_property_ids)

    for query_data in recent_queries:
        query_text = query_data["query"]
        try:
            query_vec = embed_text(query_text)
            qdrant_results = await qdrant_search_properties(
                query_vector=query_vec,
                limit=limit,
                filters=None,
            )
            for result in qdrant_results:
                prop_id = result.get("id")
                if prop_id and prop_id not in seen_ids:
                    seen_ids.add(prop_id)
                    all_results.append({
                        "id": prop_id,
                        "score": result.get("score", 0.0),
                        "timestamp": query_data.get("timestamp"),
                    })
        except Exception as e:
            print(f"[RECOMMENDATIONS] Error searching for query '{query_text}': {e}")

    if not all_results:
        return {"properties": [], "count": 0}

    def _sort_key(result: Dict[str, Any]) -> tuple:
        score = result.get("score", 0.0)
        ts = result.get("timestamp", datetime.min)
        return (-score, ts.timestamp() if isinstance(ts, datetime) else 0)

    all_results.sort(key=_sort_key)
    top_property_ids = [r["id"] for r in all_results[: limit * 2]]

    properties = await property_repo.list_by_ids(top_property_ids)
    by_id = {p["id"]: p for p in properties}
    ordered = [by_id[pid] for pid in top_property_ids if pid in by_id][:limit]
    return {"properties": ordered, "count": len(ordered)}


async def get_popular_properties(
    property_repo: "PropertyRepository",
    limit: int,
) -> Dict[str, Any]:
    """Get popular/recent properties (Postgres)."""
    try:
        properties = await property_repo.list_recent(limit)
        return {"properties": properties, "count": len(properties), "source": "popular"}
    except Exception as e:
        print(f"[RECOMMENDATIONS] Error fetching popular properties: {e}")
        return {"properties": [], "count": 0, "source": "popular"}


# Type hints (avoid circular import)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from common.repositories.chat_history_repository import ChatHistoryRepository
    from common.repositories.property_repository import PropertyRepository
