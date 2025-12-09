"""
Tools for creating property listings.
"""
import asyncio
import concurrent.futures
from typing import Any, Dict, Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
from services.embeddings.service import embed_text
import os
from dotenv import load_dotenv
from bson import ObjectId
from datetime import datetime

# Load environment variables
load_dotenv()

def get_database_client():
    """Create a fresh database client for each request."""
    mongodb_url = os.getenv("MONGODB_URL")
    if not mongodb_url:
        raise ValueError("MONGODB_URL environment variable is required")
    return AsyncIOMotorClient(mongodb_url)

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
    """
    Asynchronously creates a new property listing in the database.
    Finds the user via clerk_id to get seller_id.
    """
    client = None
    try:
        client = get_database_client()
        db = client["proppal"]

        # 1. Find the user by clerk_id
        if not clerk_id:
            return {"success": False, "error": "No clerk_id was provided."}

        user = await db["users"].find_one({"clerk_id": clerk_id}, {"_id": 1})
        if not user:
            return {"success": False, "error": "User with the specified Clerk ID not found."}

        seller_id = user["_id"]

        # 2. Prepare the property document
        property_doc = {
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
            "seller_id": seller_id,
            "images": images or [],
            "metadata": metadata or {},
            "embeddings": embed_text(f"Property: {title}. Description: {description}. Location: {city}, {area}. Type: {property_type}."),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        # 3. Insert the new property
        result = await db["properties"].insert_one(property_doc)

        if result.inserted_id:
            return {
                "success": True,
                "property_id": str(result.inserted_id),
                "message": f"Successfully created property listing: '{title}'."
            }
        else:
            return {"success": False, "error": "Failed to insert the property into the database."}

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if client:
            client.close()

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

