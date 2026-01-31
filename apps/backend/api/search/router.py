"""
Property search API with vector similarity search using Qdrant.
Fetches full property docs from PostgreSQL (Neon) by UUID.
"""
from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from common.repositories.property_repository import PropertyRepository, get_property_repository
from services.embeddings.service import embed_text
from services.vector_search.qdrant_service import search_properties as qdrant_search_properties


router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/properties")
async def search_properties(
    body: Dict[str, Any],
    property_repo: PropertyRepository = Depends(get_property_repository),
):
    """
    Search properties using vector similarity search with Qdrant.
    Full documents are fetched from PostgreSQL by UUID (from Qdrant payload).
    """
    query_text: str = body.get("query", "")
    k: int = int(body.get("k", 5))

    if not query_text:
        return {"count": 0, "results": []}

    query_vec = embed_text(query_text)

    filters: Dict[str, Any] = {}
    city = body.get("city")
    price_min = body.get("price_min")
    price_max = body.get("price_max")
    if city:
        filters["city"] = city
    if price_min is not None:
        filters["price_min"] = float(price_min)
    if price_max is not None:
        filters["price_max"] = float(price_max)

    qdrant_results = await qdrant_search_properties(
        query_vector=query_vec,
        limit=k,
        filters=filters if filters else None,
    )

    if not qdrant_results:
        return {"count": 0, "results": []}

    # Qdrant returns UUID strings in payload; skip invalid IDs
    import uuid as uuid_module
    property_ids: List[str] = []
    for result in qdrant_results:
        prop_id = result.get("id")
        if prop_id:
            try:
                uuid_module.UUID(str(prop_id))
                property_ids.append(str(prop_id))
            except (ValueError, TypeError, AttributeError):
                continue

    if not property_ids:
        return {"count": 0, "results": []}

    properties = await property_repo.list_by_ids(property_ids)

    score_map = {r["id"]: r["score"] for r in qdrant_results}
    for prop in properties:
        prop["score"] = score_map.get(prop["id"], 0.0)
    results = sorted(properties, key=lambda x: x.get("score", 0), reverse=True)

    return {"count": len(results), "results": results}
