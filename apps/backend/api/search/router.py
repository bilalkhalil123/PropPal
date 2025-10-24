"""
Property search API with vector similarity search
"""
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.db import get_database
from services.embeddings.service import embed_text


router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/properties")
async def search_properties(
    body: Dict[str, Any],
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Search properties using vector similarity search

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

    # Optional filters
    city = body.get("city")
    price_min = body.get("price_min")
    price_max = body.get("price_max")

    if city or price_min is not None or price_max is not None:
        match: Dict[str, Any] = {}
        if city:
            match["city"] = city
        price_cond: Dict[str, Any] = {}
        if price_min is not None:
            price_cond["$gte"] = float(price_min)
        if price_max is not None:
            price_cond["$lte"] = float(price_max)
        if price_cond:
            match["price"] = price_cond
        pipeline.insert(1, {"$match": match})

    # Execute search
    results = await db["properties"].aggregate(pipeline).to_list(k)

    # Normalize _id for JSON serialization
    for r in results:
        if "_id" in r:
            r["_id"] = str(r["_id"])

    return {"count": len(results), "results": results}
