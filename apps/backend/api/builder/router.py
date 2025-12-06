from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query, UploadFile, File
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from pydantic import BaseModel

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
    profile = await db["builder_profiles"].find_one(
        {"user_id": user_id}, {"embeddings": 0}
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Builder profile not found for this user.",
        )
    # Ensure created_at and updated_at are present
    import datetime
    if "created_at" not in profile or not profile["created_at"]:
        # Use ObjectId timestamp if present, else utcnow()
        oid = profile.get("_id")
        if hasattr(oid, "generation_time"):
            profile["created_at"] = oid.generation_time
        else:
            profile["created_at"] = datetime.datetime.utcnow()
    if "updated_at" not in profile or not profile["updated_at"]:
        profile["updated_at"] = profile["created_at"]
    # Ensure portfolio_images is a list (for older profiles that may have None)
    if profile.get("portfolio_images") is None:
        profile["portfolio_images"] = []
    return profile


class BuilderProfileCreateRequest(BaseModel):
    """Request body for creating a builder profile"""
    company_name: str
    city: str
    specialization: List[str]
    experience_years: int
    about: str
    portfolio_images: Optional[List[str]] = []


@router.post(
    "/profile",
    response_model=BuilderProfileResponse,
    summary="Create a new builder profile",
)
async def create_builder_profile(
    body: BuilderProfileCreateRequest,
    clerk_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Creates a new builder profile for a user identified by their Clerk ID.
    """
    import datetime
    
    # 1. Find the user by clerk_id to get their internal user_id
    user = await db["users"].find_one({"clerk_id": clerk_id}, {"_id": 1})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with the specified Clerk ID not found.",
        )

    user_id = user["_id"]

    # 2. Check if a profile already exists for this user
    existing_profile = await db["builder_profiles"].find_one({"user_id": user_id})
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A builder profile already exists for this user.",
        )

    # 3. Prepare the profile document
    now = datetime.datetime.utcnow()
    profile_doc = {
        "user_id": user_id,
        "company_name": body.company_name,
        "specialization": body.specialization,
        "experience_years": body.experience_years,
        "about": body.about,
        "location": {"city": body.city, "latitude": 0.0, "longitude": 0.0},
        "portfolio_images": body.portfolio_images or [],
        "rating": None,
        "founded_year": None,
        "embeddings": embed_text(f"Builder: {body.company_name}. Specializes in {', '.join(body.specialization)}. About: {body.about}"),
        "created_at": now,
        "updated_at": now,
    }

    # 4. Insert the new profile
    result = await db["builder_profiles"].insert_one(profile_doc)

    if not result.inserted_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create builder profile.",
        )

    # 5. Fetch and return the created profile
    profile = await db["builder_profiles"].find_one(
        {"_id": result.inserted_id}, {"embeddings": 0}
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
    profile = await db["builder_profiles"].find_one(
        {"user_id": current_user.id}, {"embeddings": 0}
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Builder profile not found for the current user.",
        )
    # Ensure portfolio_images is a list (for older profiles that may have None)
    if profile.get("portfolio_images") is None:
        profile["portfolio_images"] = []
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
    services_cursor = db["builder_services"].find(
        {"builder_id": builder_id}, {"embeddings": 0}
    )
    services = await services_cursor.to_list(length=None)
    # Ensure service_images and service_features are lists (for older services that may have None)
    for service in services:
        if service.get("service_images") is None:
            service["service_images"] = []
        if service.get("service_features") is None:
            service["service_features"] = []
    return services


class BuilderServiceCreateRequest(BaseModel):
    """Request body for creating a builder service"""
    title: str
    description: str
    category: str
    base_price: float
    price_unit: str
    service_features: Optional[List[str]] = []
    estimated_duration: Optional[str] = None
    service_images: Optional[List[str]] = []


@router.post(
    "/service",
    response_model=BuilderServiceResponse,
    summary="Create a new builder service",
)
async def create_builder_service(
    body: BuilderServiceCreateRequest,
    clerk_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Creates a new builder service for a user identified by their Clerk ID.
    The user must already have a builder profile.
    """
    import datetime
    
    # 1. Find the user by clerk_id to get their internal user_id
    user = await db["users"].find_one({"clerk_id": clerk_id}, {"_id": 1})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with the specified Clerk ID not found.",
        )

    user_id = user["_id"]

    # 2. Find the builder profile to get the builder_id
    profile = await db["builder_profiles"].find_one({"user_id": user_id}, {"_id": 1})
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Builder profile not found. Please create a builder profile first.",
        )

    builder_id = profile["_id"]

    # 3. Prepare the service document
    now = datetime.datetime.utcnow()
    service_doc = {
        "builder_id": builder_id,
        "title": body.title,
        "description": body.description,
        "category": body.category,
        "base_price": body.base_price,
        "price_unit": body.price_unit,
        "service_features": body.service_features or [],
        "estimated_duration": body.estimated_duration,
        "service_images": body.service_images or [],
        "embeddings": embed_text(f"Builder Service: {body.title}. Category: {body.category}. Description: {body.description}"),
        "created_at": now,
        "updated_at": now,
    }

    # 4. Insert the new service
    result = await db["builder_services"].insert_one(service_doc)

    if not result.inserted_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create builder service.",
        )

    # 5. Fetch and return the created service
    service = await db["builder_services"].find_one(
        {"_id": result.inserted_id}, {"embeddings": 0}
    )
    return service


@router.delete(
    "/profile/{clerk_id}",
    summary="Delete a builder profile and its services by Clerk ID",
)
async def delete_builder_profile_by_clerk(
    clerk_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Deletes a builder profile identified by the user's Clerk ID and removes all
    services associated with that profile. This operation is idempotent for services
    removal but will 404 if the user or profile does not exist.
    """
    # 1) Resolve user by clerk_id
    user = await db["users"].find_one({"clerk_id": clerk_id}, {"_id": 1})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with the specified Clerk ID not found.",
        )

    # 2) Resolve builder profile by user_id
    user_id = user["_id"]
    profile = await db["builder_profiles"].find_one({"user_id": user_id}, {"_id": 1})
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Builder profile not found for this user.",
        )

    builder_id = profile["_id"]

    # 3) Delete all services first
    services_result = await db["builder_services"].delete_many({"builder_id": builder_id})

    # 4) Delete the profile
    profile_result = await db["builder_profiles"].delete_one({"_id": builder_id})
    if profile_result.deleted_count != 1:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete builder profile.",
        )

    return {
        "success": True,
        "deleted_services_count": getattr(services_result, "deleted_count", 0),
        "message": "Builder profile and associated services deleted successfully.",
    }

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
    services_cursor = db["builder_services"].find(
        {"builder_id": builder_id}, {"embeddings": 0}
    )
    services = await services_cursor.to_list(length=None)
    # Ensure service_images and service_features are lists (for older services that may have None)
    for service in services:
        if service.get("service_images") is None:
            service["service_images"] = []
        if service.get("service_features") is None:
            service["service_features"] = []

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


@router.get(
    "/profiles/id/{builder_id}",
    summary="Get a builder profile by its ObjectId",
)
async def get_builder_profile_by_id(
    builder_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Fetch a builder profile document by its ObjectId (from `builder_profiles`)."""
    try:
        _id = ObjectId(builder_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid builder id")

    profile = await db["builder_profiles"].find_one({"_id": _id}, {"embeddings": 0})
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    # Normalize ids
    if profile.get("_id") is not None:
        profile["_id"] = str(profile["_id"])
    if profile.get("user_id") is not None:
        profile["user_id"] = str(profile["user_id"]) if isinstance(profile["user_id"], ObjectId) else profile["user_id"]
    # Ensure portfolio_images is a list (for older profiles that may have None)
    if profile.get("portfolio_images") is None:
        profile["portfolio_images"] = []
    return profile


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


# Helper function for generating descriptions with LLM
def _generate_builder_description_with_llm(data: Dict[str, Any], description_type: str = "profile") -> str:
    """
    Generate a professional description for builder profile or service using LLM.
    """
    from groq import Groq
    from dotenv import load_dotenv
    load_dotenv()
    
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    if description_type == "profile":
        prompt = f"""Generate a professional and compelling builder profile description based on the following information. 
The description should be 2-3 paragraphs, highlighting the company's strengths, experience, and specializations.
Make it engaging and professional.

Company Name: {data.get('company_name', 'N/A')}
Specializations: {data.get('specialization', 'N/A')}
Experience: {data.get('experience_years', 'N/A')} years
City: {data.get('city', 'N/A')}
Current About (if any): {data.get('about', 'Not provided')}

Generate only the description text, no titles or headers."""
    else:  # service
        prompt = f"""Generate a professional and compelling service description based on the following information.
The description should be 1-2 paragraphs, highlighting the service benefits, features, and value proposition.
Make it engaging and professional.

Service Title: {data.get('title', 'N/A')}
Category: {data.get('category', 'N/A')}
Base Price: {data.get('base_price', 'N/A')} {data.get('price_unit', '')}
Features: {data.get('service_features', 'N/A')}
Current Description (if any): {data.get('description', 'Not provided')}

Generate only the description text, no titles or headers."""

    chat_completion = groq_client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are a professional copywriter specializing in construction and builder services marketing."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        model="llama-3.1-8b-instant",
        temperature=0.7,
        max_tokens=500
    )
    
    return chat_completion.choices[0].message.content.strip()


@router.post("/generate-description", summary="Generate builder profile description using LLM")
async def generate_builder_description(
    profile_data: Dict[str, Any] = Body(...),
    clerk_id: str = Query(..., description="Clerk user ID"),
):
    """
    Generates a builder profile description using LLM based on provided details.
    """
    try:
        description = _generate_builder_description_with_llm(profile_data, "profile")
        return {"description": description}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate description: {str(e)}"
        )


@router.post("/service/generate-description", summary="Generate builder service description using LLM")
async def generate_service_description(
    service_data: Dict[str, Any] = Body(...),
    clerk_id: str = Query(..., description="Clerk user ID"),
):
    """
    Generates a builder service description using LLM based on provided details.
    """
    try:
        description = _generate_builder_description_with_llm(service_data, "service")
        return {"description": description}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate description: {str(e)}"
        )


@router.post("/transcribe-audio", summary="Transcribe audio file to text using Groq Whisper")
async def transcribe_builder_audio(
    audio_file: UploadFile = File(...),
    clerk_id: str = Query(..., description="Clerk user ID"),
):
    """
    Transcribes an audio file to text using Groq's Whisper API for builder profiles/services.
    Accepts: MP3, WAV, OGG, WebM, M4A (max 25MB)
    """
    try:
        # Validate file type
        valid_types = [
            'audio/mpeg',
            'audio/mp3', 
            'audio/wav',
            'audio/ogg',
            'audio/webm',
            'audio/m4a',
            'audio/x-m4a',
        ]
        
        file_extension = os.path.splitext(audio_file.filename)[1].lower()
        valid_extensions = ['.mp3', '.wav', '.ogg', '.webm', '.m4a']
        
        if audio_file.content_type not in valid_types and file_extension not in valid_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid audio file type. Supported formats: MP3, WAV, OGG, WebM, M4A"
            )
        
        # Read file content
        file_content = await audio_file.read()
        file_size = len(file_content)
        
        # Validate file size (max 25MB)
        if file_size > 25 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio file too large. Maximum size is 25MB."
            )
        
        # Save to temporary file for Groq API
        temp_file_path = None
        try:
            # Create temp file with proper extension
            with tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=file_extension,
                mode='wb'
            ) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            # Transcribe using Groq Whisper
            from groq import Groq
            from dotenv import load_dotenv
            load_dotenv()
            
            groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            
            with open(temp_file_path, "rb") as audio:
                transcription = groq_client.audio.transcriptions.create(
                    file=(audio_file.filename, audio.read()),
                    model="whisper-large-v3-turbo",
                    response_format="json",
                    language="en",
                    temperature=0.0
                )
            
            transcript = transcription.text.strip()
            
            if not transcript:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No speech detected in audio file"
                )
            
            return {
                "success": True,
                "transcript": transcript,
                "filename": audio_file.filename,
                "size_bytes": file_size
            }
            
        finally:
            # Clean up temp file
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transcribe audio: {str(e)}"
        )