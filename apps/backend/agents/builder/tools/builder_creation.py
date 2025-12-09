"""
Tools for creating builder-related entities like profiles and services.
"""
import asyncio
import concurrent.futures
from typing import Any, Dict, Optional
from langchain_core.tools import tool
from motor.motor_asyncio import AsyncIOMotorClient
from services.embeddings.service import embed_text
from services.vector_search.qdrant_service import (
    upsert_builder_profile_embedding,
    upsert_builder_service_embedding,
)
import os
from typing import List
from dotenv import load_dotenv
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_database_client():
    """Create a fresh database client for each request."""
    mongodb_url = os.getenv("MONGODB_URL")
    if not mongodb_url:
        raise ValueError("MONGODB_URL environment variable is required")
    return AsyncIOMotorClient(mongodb_url)

async def _check_builder_profile_exists_async(clerk_id: str) -> Dict[str, Any]:
    """
    Asynchronously checks if a builder profile exists for a given clerk_id.
    Returns detailed status about user existence and profile existence.
    """
    client = None
    try:
        client = get_database_client()
        db = client["proppal"]

        # 1. Validate clerk_id
        if not clerk_id:
            return {
                "exists": False, 
                "user_exists": False,
                "error": "No clerk_id was provided."
            }

        # 2. Find the user by clerk_id
        user = await db["users"].find_one({"clerk_id": clerk_id}, {"_id": 1})
        if not user:
            return {
                "exists": False,
                "user_exists": False,
                "error": "User with the specified Clerk ID not found."
            }

        # 3. User exists, now check for builder profile
        user_id = user["_id"]
        profile = await db["builder_profiles"].find_one({"user_id": user_id}, {"_id": 1})
        
        if profile:
            return {
                "exists": True,
                "user_exists": True,
                "error": None
            }
        else:
            return {
                "exists": False,
                "user_exists": True,
                "error": None  # No error - user exists but no profile
            }
    finally:
        if client:
            client.close()

def _run_async_safely(coro):
    """Run an async coroutine from sync code, even if a loop is already running."""
    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        return asyncio.run(coro)

def check_builder_profile_exists(clerk_id: str) -> Dict[str, Any]:
    """Synchronous wrapper to check if a builder profile exists for a given clerk_id."""
    return _run_async_safely(_check_builder_profile_exists_async(clerk_id=clerk_id))

async def _create_service_async(
    clerk_id: str,
    title: str,
    description: str,
    category: str,
    base_price: float,
    price_unit: str,
    service_features: Optional[list[str]] = None,
    estimated_duration: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Asynchronously creates a new builder service in the database.
    Finds the user via clerk_id.
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

        # 2. Find the builder profile using the user_id to get the builder_id
        user_id = user["_id"]
        profile = await db["builder_profiles"].find_one({"user_id": user_id}, {"_id": 1})
        if not profile:
            return {"success": False, "error": "Builder profile not found for this user. Please create a profile first."}

        builder_id = profile["_id"]

        # 3. Prepare the service document
        service_doc = {
            "builder_id": builder_id,
            "title": title,
            "description": description,
            "category": category,
            "base_price": base_price,
            "price_unit": price_unit,
            "service_features": service_features or [],
            "estimated_duration": estimated_duration,
            "embeddings": embed_text(f"Service: {title}. Description: {description}"),
        }
        
        # 4. Insert the new service
        result = await db["builder_services"].insert_one(service_doc)

        if result.inserted_id:
            service_id_str = str(result.inserted_id)
            
            # 5. Store embedding in Qdrant for vector search
            try:
                embedding = service_doc.get("embeddings")
                if embedding:
                    # Get city from builder profile for metadata
                    profile_full = await db["builder_profiles"].find_one({"_id": builder_id}, {"location": 1})
                    city = profile_full.get("location", {}).get("city", "") if profile_full else ""
                    
                    qdrant_metadata = {
                        "title": title,
                        "category": category,
                        "base_price": base_price,
                        "price_unit": price_unit,
                        "city": city,
                    }
                    if estimated_duration:
                        qdrant_metadata["estimated_duration"] = estimated_duration
                    
                    await upsert_builder_service_embedding(
                        service_id=service_id_str,
                        embedding=embedding,
                        metadata=qdrant_metadata,
                    )
                    logger.info(f"Successfully stored service embedding in Qdrant for service_id: {service_id_str}")
            except Exception as e:
                # Don't fail the creation if Qdrant fails, but log it
                logger.warning(f"Failed to store service embedding in Qdrant: {e}")
            
            return {"success": True, "service_id": service_id_str, "message": f"Successfully created service: '{title}'."}
        else:
            return {"success": False, "error": "Failed to insert the service into the database."}

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if client:
            client.close()

async def _create_profile_async(
    clerk_id: str,
    company_name: str,
    specialization: List[str],
    experience_years: int,
    about: str,
    city: str,
) -> Dict[str, Any]:
    """
    Asynchronously creates a new builder profile, but only if one doesn't already exist for the user.
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
        user_id = user["_id"]

        # 2. CHECK IF A PROFILE ALREADY EXISTS FOR THIS USER
        existing_profile = await db["builder_profiles"].find_one({"user_id": user_id})
        if existing_profile:
            return {"success": False, "error": "A builder profile already exists for this user. You can only have one."}

        # 3. Prepare the profile document
        profile_doc = {
            "user_id": user_id,
            "company_name": company_name,
            "specialization": specialization,
            "experience_years": experience_years,
            "about": about,
            "location": {"city": city, "latitude": 0.0, "longitude": 0.0}, # Placeholder coordinates
            "embeddings": embed_text(f"Builder: {company_name}. Specializes in {', '.join(specialization)}. About: {about}"),
        }

        # 4. Insert the new profile
        result = await db["builder_profiles"].insert_one(profile_doc)

        if result.inserted_id:
            profile_id_str = str(result.inserted_id)
            
            # 5. Store embedding in Qdrant for vector search
            try:
                embedding = profile_doc.get("embeddings")
                if embedding:
                    qdrant_metadata = {
                        "company_name": company_name,
                        "city": city,
                        "specialization": specialization,
                        "experience_years": experience_years,
                    }
                    
                    await upsert_builder_profile_embedding(
                        profile_id=profile_id_str,
                        embedding=embedding,
                        metadata=qdrant_metadata,
                    )
                    logger.info(f"Successfully stored profile embedding in Qdrant for profile_id: {profile_id_str}")
            except Exception as e:
                # Don't fail the creation if Qdrant fails, but log it
                logger.warning(f"Failed to store profile embedding in Qdrant: {e}")
            
            return {"success": True, "profile_id": profile_id_str, "message": f"Successfully created builder profile for '{company_name}'."}
        else:
            return {"success": False, "error": "Failed to insert the profile into the database."}

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if client:
            client.close()

@tool
def create_builder_profile_tool(
    clerk_id: str,
    company_name: str,
    specialization: List[str],
    experience_years: int,
    about: str,
    city: str,
) -> Dict[str, Any]:
    """Creates a new builder profile for a user if one does not already exist. You must have all arguments before calling this tool."""
    return create_builder_profile_sync(
        clerk_id=clerk_id,
        company_name=company_name,
        specialization=specialization,
        experience_years=experience_years,
        about=about,
        city=city,
    )

def create_builder_profile_sync(
    clerk_id: str,
    company_name: str,
    specialization: List[str],
    experience_years: int,
    about: str,
    city: str,
) -> Dict[str, Any]:
    """Synchronous entry point to create a builder profile (non-tooled)."""
    return _run_async_safely(_create_profile_async(clerk_id, company_name, specialization, experience_years, about, city))

@tool
def create_builder_service_tool(
    clerk_id: str,
    title: str,
    description: str,
    category: str,
    base_price: float,
    price_unit: str,
    service_features: Optional[list[str]] = None,
    estimated_duration: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates a new service for a builder.
    You must have all the required arguments (clerk_id, title, description, category, base_price, price_unit) before calling this tool.
    Ask the user for any missing information.
    The clerk_id is the unique identifier for the user who is creating the service.
    """
    # This sync wrapper is needed because LangChain tools are synchronous
    return create_builder_service_sync(
        clerk_id=clerk_id,
        title=title,
        description=description,
        category=category,
        base_price=base_price,
        price_unit=price_unit,
        service_features=service_features,
        estimated_duration=estimated_duration,
    )

def create_builder_service_sync(
    clerk_id: str,
    title: str,
    description: str,
    category: str,
    base_price: float,
    price_unit: str,
    service_features: Optional[list[str]] = None,
    estimated_duration: Optional[str] = None,
) -> Dict[str, Any]:
    """Synchronous entry point to create a builder service (non-tooled)."""
    return _run_async_safely(_create_service_async(
        clerk_id, title, description, category, base_price, price_unit, service_features, estimated_duration
    ))
