from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

# Add parent directory to path to import services module
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.db import get_database
from models.builder_profiles import BuilderProfileResponse
from models.builder_services import BuilderServiceResponse
from models.users import User
from services.auth.utils import get_current_user
from services.embeddings.service import embed_text

router = APIRouter(prefix="/api/builder", tags=["builder"])


@router.get(
    "/profile/{clerk_id}",
    response_model=BuilderProfileResponse,
    summary="Get a builder's profile by their Clerk ID",
)
async def get_builder_profile_by_clerk(
    clerk_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Retrieves a builder profile using the associated user's Clerk ID.
    """
    # 1. Find the user by clerk_id to get their internal user_id
    user = await db["users"].find_one({"clerk_id": clerk_id}, {"_id": 1})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with the specified Clerk ID not found.",
        )

    # 2. Find the builder profile using the internal user_id
    user_id = user["_id"]
    profile = await db["builder_profiles"].find_one({"user_id": user_id})
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Builder profile not found for this user.",
        )
    return profile


@router.get(
    "/profile/me/",
    response_model=BuilderProfileResponse,
    summary="Get the current user's builder profile",
)
async def get_my_builder_profile(
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves the builder profile associated with the currently authenticated user.
    """
    profile = await db["builder_profiles"].find_one({"user_id": current_user.id})
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Builder profile not found for the current user.",
        )
    return profile


@router.get(
    "/services/{clerk_id}",
    response_model=List[BuilderServiceResponse],
    summary="Get a builder's services by their Clerk ID",
)
async def get_builder_services_by_clerk(
    clerk_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Retrieves all services for a builder using the associated user's Clerk ID.
    """
    # 1. Find the user by clerk_id to get their internal user_id
    user = await db["users"].find_one({"clerk_id": clerk_id}, {"_id": 1})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with the specified Clerk ID not found.",
        )

    # 2. Find the builder profile using the user_id to get the builder_id
    user_id = user["_id"]
    profile = await db["builder_profiles"].find_one({"user_id": user_id}, {"_id": 1})
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Builder profile not found for this user.",
        )

    # 3. Find services using the builder_id from the profile
    builder_id = profile["_id"]
    services_cursor = db["builder_services"].find({"builder_id": builder_id})
    services = await services_cursor.to_list(length=None)
    return services


@router.get(
    "/services/me/",
    response_model=List[BuilderServiceResponse],
    summary="Get the current builder's services",
)
async def get_my_builder_services(
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves all services associated with the currently authenticated builder's profile.
    """
    # First, find the builder profile to get its ID
    profile = await db["builder_profiles"].find_one(
        {"user_id": current_user.id}, {"_id": 1}
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Builder profile not found for the current user.",
        )

    builder_id = profile["_id"]

    # Then, find all services associated with that builder_id
    services_cursor = db["builder_services"].find({"builder_id": builder_id})
    services = await services_cursor.to_list(length=None)

    return services


from typing import Any, Dict, List

@router.post("/profiles/search", summary="Search for builder profiles")
async def search_builders(
    body: Dict[str, Any],
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Searches for builder profiles using a query string and optional filters.
    """
    query_text: str = body.get("query", "")
    k: int = int(body.get("k", 10))
    if not query_text:
        return {"count": 0, "results": []}

    query_vec = embed_text(query_text)

    # --- Start of Changes ---

    # Build the vector search stage
    search_stage = {
        "$vectorSearch": {
            "index": "builder_profile_index",
            "path": "embeddings",
            "queryVector": query_vec,
            "numCandidates": max(50, k * 5),
            "limit": k,
        }
    }

    # Build the filter query using MQL
    city = body.get("city")
    if city:
        # Correctly add the MQL filter to the $vectorSearch stage
        search_stage["$vectorSearch"]["filter"] = {
            "location.city": city
        }

    pipeline: List[Dict[str, Any]] = [
        search_stage,
        {
            "$project": {
                "score": {"$meta": "vectorSearchScore"},
                "_id": 1,
                "company_name": 1,
                "specialization": 1,
                "experience_years": 1,
                "rating": 1,
                "location": 1,
                "about": 1
            }
        },
    ]
    # --- End of Changes ---

    results = await db["builder_profiles"].aggregate(pipeline).to_list(k)
    for r in results:
        if "_id" in r:
            r["_id"] = str(r["_id"])
    return {"count": len(results), "results": results}


@router.post("/services/search", summary="Search for builder services")
async def search_builder_services(
    body: Dict[str, Any],
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Searches for builder services using a query string and optional filters.
    """
    query_text: str = body.get("query", "")
    k: int = int(body.get("k", 10))
    if not query_text:
        return {"count": 0, "results": []}

    query_vec = embed_text(query_text)

    # --- Start of Changes ---

    # Build the vector search stage
    search_stage = {
        "$vectorSearch": {
            "index": "builder_service_index",
            "path": "embeddings",
            "queryVector": query_vec,
            "numCandidates": max(50, k * 5),
            "limit": k,
        }
    }

    # Build the filter document using MQL
    filters = {}
    category = body.get("category")
    price_min = body.get("price_min")
    price_max = body.get("price_max")

    if category:
        filters["category"] = category

    if price_min is not None or price_max is not None:
        price_cond = {}
        if price_min is not None:
            price_cond["$gte"] = float(price_min)
        if price_max is not None:
            price_cond["$lte"] = float(price_max)
        filters["base_price"] = price_cond
    
    # If any filters exist, add them to the $vectorSearch stage
    if filters:
        search_stage["$vectorSearch"]["filter"] = filters

    pipeline: List[Dict[str, Any]] = [
        search_stage,
        {
            "$project": {
                "score": {"$meta": "vectorSearchScore"},
                "_id": 1,
                "title": 1,
                "description": 1,
                "category": 1,
                "base_price": 1,
                "price_unit": 1,
                "builder_id": 1,
                "service_features": 1
            }
        },
    ]
    # --- End of Changes ---

    results = await db["builder_services"].aggregate(pipeline).to_list(k)
    for r in results:
        if "_id" in r:
            r["_id"] = str(r["_id"])
        if "builder_id" in r:
            r["builder_id"] = str(r["builder_id"])
    return {"count": len(results), "results": results}