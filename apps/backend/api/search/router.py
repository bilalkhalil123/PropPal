"""
Property search API with vector similarity search using Qdrant
"""
from typing import Any, Dict, List
from bson import ObjectId

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.db import get_database
from services.embeddings.service import embed_text
from services.vector_search.qdrant_service import search_properties as qdrant_search_properties


router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/properties")
async def search_properties(
    body: Dict[str, Any],
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Search properties using vector similarity search with Qdrant

    Body:
        query: Search query text
        k: Number of results to return (default: 10)
        city: Optional city filter
        price_min: Optional minimum price filter
        price_max: Optional maximum price filter
    """
    query_text: str = body.get("query", "")
    k: int = int(body.get("k", 5))

    if not query_text:
        return {"count": 0, "results": []}

    # Generate query embedding
    query_vec = embed_text(query_text)

    # Prepare filters for Qdrant
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

    # Search in Qdrant
    qdrant_results = await qdrant_search_properties(
        query_vector=query_vec,
        limit=k,
        filters=filters if filters else None,
    )

    if not qdrant_results:
        return {"count": 0, "results": []}

    # Fetch full documents from MongoDB using the IDs from Qdrant
    property_ids = []
    for result in qdrant_results:
        prop_id = result.get("id")
        if prop_id:
            try:
                property_ids.append(ObjectId(prop_id))
            except Exception:
                # Skip invalid ObjectIds
                continue
    
    if not property_ids:
        return {"count": 0, "results": []}

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

    return {"count": len(results), "results": results}
