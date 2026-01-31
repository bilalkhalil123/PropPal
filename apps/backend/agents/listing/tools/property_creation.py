"""
Tools for creating property listings. Uses Postgres (UserRepository, PropertyRepository); IDs are UUID strings.
"""
import asyncio
import concurrent.futures
from typing import Any, Dict, Optional, List

from common.db import get_db_session_ctx
from common.repositories.user_repository import UserRepository
from common.repositories.property_repository import PropertyRepository
from services.embeddings.service import embed_text


def _run_async_safely(coro):
    """Run an async coroutine from sync code, even if a loop is already running."""
    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        return asyncio.run(coro)


async def _create_property_async(
    clerk_id: str,
    title: str,
    description: str,
    price: float,
    property_type: str,
    area_sqft: float,
    bedrooms: int,
    bathrooms: int,
    floors: int,
    city: str,
    area: str,
    lng: float,
    lat: float,
    images: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Creates a new property listing. Finds user via clerk_id; inserts in Postgres; upserts embedding to Qdrant."""
    try:
        if not clerk_id:
            return {"success": False, "error": "No clerk_id was provided."}
        async with get_db_session_ctx() as session:
            user_repo = UserRepository(session)
            property_repo = PropertyRepository(session)
            user = await user_repo.get_by_clerk_id(clerk_id)
            if not user:
                return {"success": False, "error": "User with the specified Clerk ID not found."}
            seller_id = user.id
            data = {
                "seller_id": seller_id,
                "title": title,
                "description": description,
                "price": price,
                "property_type": property_type.lower(),
                "area_sqft": area_sqft,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "floors": floors,
                "city": city,
                "area": area,
                "lng": lng,
                "lat": lat,
                "images": images or [],
                "metadata": metadata or {},
            }
            row = await property_repo.create(data)
            property_id_str = row.id
        embedding = embed_text(f"Property: {title}. Description: {description}. Location: {city}, {area}. Type: {property_type}.")
        try:
            from services.vector_search.qdrant_service import upsert_property_embedding
            await upsert_property_embedding(
                property_id=property_id_str,
                embedding=embedding,
                metadata={
                    "title": title,
                    "city": city,
                    "area": area,
                    "property_type": property_type.lower(),
                    "bedrooms": bedrooms,
                    "bathrooms": bathrooms,
                    "price": price,
                },
            )
        except Exception as qe:
            print(f"[WARN] Failed to upsert property embedding to Qdrant: {qe}")
        return {
            "success": True,
            "property_id": property_id_str,
            "message": f"Successfully created property listing: '{title}'."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def create_property_sync(
    clerk_id: str,
    title: str,
    description: str,
    price: float,
    property_type: str,
    area_sqft: float,
    bedrooms: int,
    bathrooms: int,
    floors: int,
    city: str,
    area: str,
    lng: float,
    lat: float,
    images: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Synchronous entry point to create a property (non-tooled)."""
    return _run_async_safely(_create_property_async(
        clerk_id, title, description, price, property_type, area_sqft,
        bedrooms, bathrooms, floors, city, area, lng, lat, images, metadata
    ))

