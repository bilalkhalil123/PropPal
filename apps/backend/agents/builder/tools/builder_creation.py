"""
Tools for creating builder-related entities like profiles and services.
"""
import asyncio
from typing import Any, Dict, Optional
from langchain_core.tools import tool
from motor.motor_asyncio import AsyncIOMotorClient
from services.embeddings.service import embed_text
import os
from typing import List
from dotenv import load_dotenv
from bson import ObjectId

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
    """
    client = None
    try:
        client = get_database_client()
        db = client["proppal"]

        # 1. Find the user by clerk_id to get their internal user_id
        user = await db["users"].find_one({"clerk_id": clerk_id}, {"_id": 1})
        if not user:
            return {"exists": False, "error": "User with the specified Clerk ID not found."}

        # 2. Find the builder profile using the user_id
        user_id = user["_id"]
        profile = await db["builder_profiles"].find_one({"user_id": user_id}, {"_id": 1})
        if not profile:
            return {"exists": False, "error": "Builder profile not found for this user. Please create a profile first."}
        
        return {"exists": True, "error": None}
    finally:
        if client:
            client.close()

def check_builder_profile_exists(clerk_id: str) -> Dict[str, Any]:
    """Synchronous wrapper to check if a builder profile exists for a given clerk_id."""
    return asyncio.run(_check_builder_profile_exists_async(clerk_id))

async def _create_service_async(
    clerk_id: str,
    title: str,
    description: str,
    category: str,
    base_price: float,
    price_unit: str,
    service_features: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """
    Asynchronously creates a new builder service in the database.
    """
    client = None
    try:
        client = get_database_client()
        db = client["proppal"]

        # 1. Find the user by clerk_id to get their internal user_id
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
            "embeddings": embed_text(f"Service: {title}. Description: {description}"),
        }
        
        # 4. Insert the new service
        result = await db["builder_services"].insert_one(service_doc)

        if result.inserted_id:
            return {"success": True, "service_id": str(result.inserted_id), "message": f"Successfully created service: '{title}'."}
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

        # 1. Find the user by clerk_id to get their internal user_id
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
            return {"success": True, "profile_id": str(result.inserted_id), "message": f"Successfully created builder profile for '{company_name}'."}
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
    return asyncio.run(_create_profile_async(clerk_id, company_name, specialization, experience_years, about, city))

@tool
def create_builder_service_tool(
    clerk_id: str,
    title: str,
    description: str,
    category: str,
    base_price: float,
    price_unit: str,
    service_features: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """
    Creates a new service for a builder.
    You must have all the required arguments (clerk_id, title, description, category, base_price, price_unit) before calling this tool.
    Ask the user for any missing information.
    The clerk_id is the unique identifier for the user who is creating the service.
    """
    # This sync wrapper is needed because LangChain tools are synchronous
    try:
        loop = asyncio.get_running_loop()
        result = loop.run_until_complete(_create_service_async(clerk_id, title, description, category, base_price, price_unit, service_features))
    except RuntimeError:
        result = asyncio.run(_create_service_async(clerk_id, title, description, category, base_price, price_unit, service_features))

    return result
