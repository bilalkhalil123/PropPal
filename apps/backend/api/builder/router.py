from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query, UploadFile, File
from pydantic import BaseModel

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.repositories.user_repository import UserRepository, get_user_repository
from common.repositories.builder_profile_repository import BuilderProfileRepository, get_builder_profile_repository
from common.repositories.builder_service_repository import BuilderServiceRepository, get_builder_service_repository
from common.uuid_utils import parse_uuid
from models.builder_profiles import BuilderProfileResponse
from models.builder_services import BuilderServiceResponse
from models.users import User
from services.auth.utils import get_current_user
from services.embeddings.service import embed_text
from services.vector_search.qdrant_service import search_builder_profiles, search_builder_services as qdrant_search_builder_services

router = APIRouter(prefix="/api/builder", tags=["builder"])


@router.get(
    "/profile/{clerk_id}",
    response_model=BuilderProfileResponse,
    summary="Get a builder's profile by their Clerk ID",
)
async def get_builder_profile_by_clerk(
    clerk_id: str,
    user_repo: UserRepository = Depends(get_user_repository),
    profile_repo: BuilderProfileRepository = Depends(get_builder_profile_repository),
):
    """Retrieves a builder profile using the associated user's Clerk ID."""
    user = await user_repo.get_by_clerk_id(clerk_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with the specified Clerk ID not found.",
        )
    profile = await profile_repo.get_by_user_id(user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Builder profile not found for this user.",
        )
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
    user_repo: UserRepository = Depends(get_user_repository),
    profile_repo: BuilderProfileRepository = Depends(get_builder_profile_repository),
):
    """Creates a new builder profile for a user identified by their Clerk ID."""
    user = await user_repo.get_by_clerk_id(clerk_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with the specified Clerk ID not found.",
        )
    existing_profile = await profile_repo.get_by_user_id(user.id)
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A builder profile already exists for this user.",
        )
    profile_doc = {
        "user_id": user.id,
        "company_name": body.company_name,
        "specialization": body.specialization,
        "experience_years": body.experience_years,
        "about": body.about,
        "location": {"city": body.city, "latitude": 0.0, "longitude": 0.0},
        "portfolio_images": body.portfolio_images or [],
        "rating": None,
        "founded_year": None,
    }
    row = await profile_repo.create(profile_doc)
    profile = profile_repo._row_to_dict(row)
    if profile.get("portfolio_images") is None:
        profile["portfolio_images"] = []
    return profile


@router.get(
    "/profile/me/",
    response_model=BuilderProfileResponse,
    summary="Get the current user's builder profile",
)
async def get_my_builder_profile(
    profile_repo: BuilderProfileRepository = Depends(get_builder_profile_repository),
    current_user: User = Depends(get_current_user),
):
    """Retrieves the builder profile associated with the currently authenticated user."""
    profile = await profile_repo.get_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Builder profile not found for the current user.",
        )
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
    user_repo: UserRepository = Depends(get_user_repository),
    profile_repo: BuilderProfileRepository = Depends(get_builder_profile_repository),
    service_repo: BuilderServiceRepository = Depends(get_builder_service_repository),
):
    """Retrieves all services for a builder using the associated user's Clerk ID."""
    user = await user_repo.get_by_clerk_id(clerk_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with the specified Clerk ID not found.",
        )
    profile = await profile_repo.get_by_user_id(user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Builder profile not found for this user.",
        )
    services = await service_repo.list_by_builder_id(profile["id"])
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
    user_repo: UserRepository = Depends(get_user_repository),
    profile_repo: BuilderProfileRepository = Depends(get_builder_profile_repository),
    service_repo: BuilderServiceRepository = Depends(get_builder_service_repository),
):
    """Creates a new builder service for a user identified by their Clerk ID."""
    user = await user_repo.get_by_clerk_id(clerk_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with the specified Clerk ID not found.",
        )
    profile = await profile_repo.get_by_user_id(user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Builder profile not found. Please create a builder profile first.",
        )
    service_doc = {
        "builder_id": profile["id"],
        "title": body.title,
        "description": body.description,
        "category": body.category,
        "base_price": body.base_price,
        "price_unit": body.price_unit,
        "service_features": body.service_features or [],
        "estimated_duration": body.estimated_duration,
        "service_images": body.service_images or [],
    }
    row = await service_repo.create(service_doc)
    return service_repo._row_to_dict(row)


@router.delete(
    "/profile/{clerk_id}",
    summary="Delete a builder profile and its services by Clerk ID",
)
async def delete_builder_profile_by_clerk(
    clerk_id: str,
    user_repo: UserRepository = Depends(get_user_repository),
    profile_repo: BuilderProfileRepository = Depends(get_builder_profile_repository),
    service_repo: BuilderServiceRepository = Depends(get_builder_service_repository),
):
    """Deletes a builder profile and all its services. 404 if user or profile not found."""
    user = await user_repo.get_by_clerk_id(clerk_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with the specified Clerk ID not found.",
        )
    profile = await profile_repo.get_by_user_id(user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Builder profile not found for this user.",
        )
    builder_id = profile["id"]
    deleted_services_count = await service_repo.delete_by_builder_id(builder_id)
    deleted = await profile_repo.delete(builder_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete builder profile.",
        )
    return {
        "success": True,
        "deleted_services_count": deleted_services_count,
        "message": "Builder profile and associated services deleted successfully.",
    }

@router.get(
    "/services/me/",
    response_model=List[BuilderServiceResponse],
    summary="Get the current builder's services",
)
async def get_my_builder_services(
    profile_repo: BuilderProfileRepository = Depends(get_builder_profile_repository),
    service_repo: BuilderServiceRepository = Depends(get_builder_service_repository),
    current_user: User = Depends(get_current_user),
):
    """Retrieves all services for the currently authenticated builder's profile."""
    profile = await profile_repo.get_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Builder profile not found for the current user.",
        )
    services = await service_repo.list_by_builder_id(profile["id"])
    for service in services:
        if service.get("service_images") is None:
            service["service_images"] = []
        if service.get("service_features") is None:
            service["service_features"] = []
    return services


@router.post("/profiles/search", summary="Search for builder profiles")
async def search_builders(
    body: Dict[str, Any],
    profile_repo: BuilderProfileRepository = Depends(get_builder_profile_repository),
):
    """Searches for builder profiles using Qdrant; full docs from Postgres by UUID."""
    query_text: str = body.get("query", "")
    k: int = int(body.get("k", 10))
    if not query_text:
        return {"count": 0, "results": []}
    query_vec = embed_text(query_text)
    filters: Dict[str, Any] = {}
    city = body.get("city")
    if city:
        filters["city"] = city
    qdrant_results = await search_builder_profiles(
        query_vector=query_vec,
        limit=k,
        filters=filters if filters else None,
    )
    if not qdrant_results:
        return {"count": 0, "results": []}
    profile_ids = [r["id"] for r in qdrant_results if r.get("id")]
    profiles = await profile_repo.list_by_ids(profile_ids)
    score_map = {r["id"]: r["score"] for r in qdrant_results}
    for p in profiles:
        p["score"] = score_map.get(p["id"], 0.0)
    results = sorted(profiles, key=lambda x: x.get("score", 0), reverse=True)
    return {"count": len(results), "results": results}


@router.get(
    "/profiles/id/{builder_id}",
    summary="Get a builder profile by UUID",
)
async def get_builder_profile_by_id(
    builder_id: str,
    profile_repo: BuilderProfileRepository = Depends(get_builder_profile_repository),
):
    """Fetch a builder profile by UUID. Returns 404 if invalid or not found."""
    bid = parse_uuid(builder_id, "builder_id")
    profile = await profile_repo.get_by_id(bid)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")
    if profile.get("portfolio_images") is None:
        profile["portfolio_images"] = []
    return profile


@router.post("/services/search", summary="Search for builder services")
async def search_builder_services(
    body: Dict[str, Any],
    service_repo: BuilderServiceRepository = Depends(get_builder_service_repository),
):
    """Searches builder services via Qdrant; full docs from Postgres by UUID."""
    query_text: str = body.get("query", "")
    k: int = int(body.get("k", 10))
    if not query_text:
        return {"count": 0, "results": []}
    query_vec = embed_text(query_text)
    filters: Dict[str, Any] = {}
    category = body.get("category")
    price_min = body.get("price_min")
    price_max = body.get("price_max")
    if category:
        filters["category"] = category
    if price_min is not None or price_max is not None:
        price_cond: Dict[str, float] = {}
        if price_min is not None:
            price_cond["$gte"] = float(price_min)
        if price_max is not None:
            price_cond["$lte"] = float(price_max)
        filters["base_price"] = price_cond
    qdrant_results = await qdrant_search_builder_services(
        query_vector=query_vec,
        limit=k,
        filters=filters if filters else None,
    )
    if not qdrant_results:
        return {"count": 0, "results": []}
    service_ids = [r["id"] for r in qdrant_results if r.get("id")]
    services = await service_repo.list_by_ids(service_ids)
    score_map = {r["id"]: r["score"] for r in qdrant_results}
    for s in services:
        s["score"] = score_map.get(s["id"], 0.0)
    results = sorted(services, key=lambda x: x.get("score", 0), reverse=True)
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