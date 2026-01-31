"""
Tools for creating builder-related entities (profiles and services). Uses Postgres; IDs are UUID strings.
"""
import asyncio
import concurrent.futures
from typing import Any, Dict, Optional, List
from langchain_core.tools import tool

from common.db import get_db_session_ctx
from common.repositories.user_repository import UserRepository
from common.repositories.builder_profile_repository import BuilderProfileRepository
from common.repositories.builder_service_repository import BuilderServiceRepository
from services.embeddings.service import embed_text
from services.vector_search.qdrant_service import (
    upsert_builder_profile_embedding,
    upsert_builder_service_embedding,
)
import logging

logger = logging.getLogger(__name__)


def _run_async_safely(coro):
    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        return asyncio.run(coro)


async def _check_builder_profile_exists_async(clerk_id: str) -> Dict[str, Any]:
    """Check if a builder profile exists for the given clerk_id (Postgres)."""
    try:
        if not clerk_id:
            return {"exists": False, "user_exists": False, "error": "No clerk_id was provided."}
        async with get_db_session_ctx() as session:
            user_repo = UserRepository(session)
            profile_repo = BuilderProfileRepository(session)
            user = await user_repo.get_by_clerk_id(clerk_id)
            if not user:
                return {"exists": False, "user_exists": False, "error": "User with the specified Clerk ID not found."}
            profile = await profile_repo.get_by_user_id(user.id)
            if profile:
                return {"exists": True, "user_exists": True, "error": None}
            return {"exists": False, "user_exists": True, "error": None}
    except Exception as e:
        return {"exists": False, "user_exists": False, "error": str(e)}


def check_builder_profile_exists(clerk_id: str) -> Dict[str, Any]:
    return _run_async_safely(_check_builder_profile_exists_async(clerk_id=clerk_id))


async def _create_service_async(
    clerk_id: str,
    title: str,
    description: str,
    category: str,
    base_price: float,
    price_unit: str,
    service_features: Optional[List[str]] = None,
    estimated_duration: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new builder service (Postgres); upsert embedding to Qdrant."""
    try:
        if not clerk_id:
            return {"success": False, "error": "No clerk_id was provided."}
        async with get_db_session_ctx() as session:
            user_repo = UserRepository(session)
            profile_repo = BuilderProfileRepository(session)
            service_repo = BuilderServiceRepository(session)
            user = await user_repo.get_by_clerk_id(clerk_id)
            if not user:
                return {"success": False, "error": "User with the specified Clerk ID not found."}
            profile = await profile_repo.get_by_user_id(user.id)
            if not profile:
                return {"success": False, "error": "Builder profile not found for this user. Please create a profile first."}
            builder_id = profile["id"]
            service_doc = {
                "builder_id": builder_id,
                "title": title,
                "description": description,
                "category": category,
                "base_price": base_price,
                "price_unit": price_unit,
                "service_features": service_features or [],
                "estimated_duration": estimated_duration,
            }
            row = await service_repo.create(service_doc)
            service_id_str = row.id
            city = (profile.get("location") or {}).get("city", "") if isinstance(profile.get("location"), dict) else ""
        try:
            embedding = embed_text(f"Service: {title}. Description: {description}")
            qdrant_metadata = {"title": title, "category": category, "base_price": base_price, "price_unit": price_unit, "city": city}
            if estimated_duration:
                qdrant_metadata["estimated_duration"] = estimated_duration
            await upsert_builder_service_embedding(service_id=service_id_str, embedding=embedding, metadata=qdrant_metadata)
            logger.info(f"Successfully stored service embedding in Qdrant for service_id: {service_id_str}")
        except Exception as e:
            logger.warning(f"Failed to store service embedding in Qdrant: {e}")
        return {"success": True, "service_id": service_id_str, "message": f"Successfully created service: '{title}'."}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _create_profile_async(
    clerk_id: str,
    company_name: str,
    specialization: List[str],
    experience_years: int,
    about: str,
    city: str,
) -> Dict[str, Any]:
    """Create a new builder profile (Postgres); upsert embedding to Qdrant."""
    try:
        if not clerk_id:
            return {"success": False, "error": "No clerk_id was provided."}
        async with get_db_session_ctx() as session:
            user_repo = UserRepository(session)
            profile_repo = BuilderProfileRepository(session)
            user = await user_repo.get_by_clerk_id(clerk_id)
            if not user:
                return {"success": False, "error": "User with the specified Clerk ID not found."}
            existing_profile = await profile_repo.get_by_user_id(user.id)
            if existing_profile:
                return {"success": False, "error": "A builder profile already exists for this user. You can only have one."}
            profile_doc = {
                "user_id": user.id,
                "company_name": company_name,
                "specialization": specialization,
                "experience_years": experience_years,
                "about": about,
                "location": {"city": city, "latitude": 0.0, "longitude": 0.0},
            }
            row = await profile_repo.create(profile_doc)
            profile_id_str = row.id
        try:
            embedding = embed_text(f"Builder: {company_name}. Specializes in {', '.join(specialization)}. About: {about}")
            qdrant_metadata = {"company_name": company_name, "city": city, "specialization": specialization, "experience_years": experience_years}
            await upsert_builder_profile_embedding(profile_id=profile_id_str, embedding=embedding, metadata=qdrant_metadata)
            logger.info(f"Successfully stored profile embedding in Qdrant for profile_id: {profile_id_str}")
        except Exception as e:
            logger.warning(f"Failed to store profile embedding in Qdrant: {e}")
        return {"success": True, "profile_id": profile_id_str, "message": f"Successfully created builder profile for '{company_name}'."}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def create_builder_profile_tool(
    clerk_id: str,
    company_name: str,
    specialization: List[str],
    experience_years: int,
    about: str,
    city: str,
) -> Dict[str, Any]:
    """Creates a new builder profile for a user if one does not already exist."""
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
    return _run_async_safely(_create_profile_async(clerk_id, company_name, specialization, experience_years, about, city))


@tool
def create_builder_service_tool(
    clerk_id: str,
    title: str,
    description: str,
    category: str,
    base_price: float,
    price_unit: str,
    service_features: Optional[List[str]] = None,
    estimated_duration: Optional[str] = None,
) -> Dict[str, Any]:
    """Creates a new service for a builder. clerk_id is the unique identifier for the user creating the service."""
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
    service_features: Optional[List[str]] = None,
    estimated_duration: Optional[str] = None,
) -> Dict[str, Any]:
    return _run_async_safely(_create_service_async(
        clerk_id, title, description, category, base_price, price_unit, service_features, estimated_duration
    ))
