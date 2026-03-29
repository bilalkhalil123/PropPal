from __future__ import annotations

from typing import Any, Dict, Union, List, Optional
from datetime import datetime
import tempfile
import os

# Ensure common module import
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, UploadFile, File, Request, BackgroundTasks

from common.uuid_utils import parse_uuid
from common.repositories.user_repository import UserRepository, get_user_repository
from common.repositories.property_repository import PropertyRepository, get_property_repository
from models.properties import PropertyCreate, PropertyCreateRequest
from models.users import User
from agents.listing.create_listing_agent import _generate_description_with_llm
from services.vector_search.qdrant_service import delete_embedding, upsert_property_embedding
from api.properties.scraper.router import router as scraper_router
from services.embeddings.service import embed_text
from services.embeddings.compose import compose_property_text
from services.auth.utils import get_current_user
from common.qdrant import PROPERTIES_COLLECTION


router = APIRouter(prefix="/api/properties", tags=["properties"])

# Include scraper-related routes
router.include_router(scraper_router)


@router.get("/{property_id}", summary="Get full property details by ID")
async def get_property_by_id(
    property_id: str,
    property_repo: PropertyRepository = Depends(get_property_repository),
):
    """
    Fetches a single property by UUID. Returns 404 if ID is invalid or not found.
    """
    pid = parse_uuid(property_id, "property_id")
    doc = await property_repo.get_by_id(pid)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return doc


@router.get("", summary="Get properties by seller (clerk_id)")
async def get_properties_by_seller(
    clerk_id: str = Query(..., description="Clerk user ID"),
    user_repo: UserRepository = Depends(get_user_repository),
    property_repo: PropertyRepository = Depends(get_property_repository),
):
    """Fetches all properties listed by a specific seller (identified by clerk_id)."""
    user = await user_repo.get_user_by_clerk_id(clerk_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with the specified Clerk ID not found."
        )
    properties = await property_repo.get_by_seller_id(user.id)
    return properties


@router.post("", summary="Create a new property listing")
async def create_property(
    property_data: PropertyCreateRequest,
    background_tasks: BackgroundTasks,
    clerk_id: str = Query(..., description="Clerk user ID"),
    user_repo: UserRepository = Depends(get_user_repository),
    property_repo: PropertyRepository = Depends(get_property_repository),
):
    """
    Creates a new property listing in the database.
    The seller_id is derived from clerk_id. Embeds and upserts to Qdrant.
    Queues a background task to fetch nearby amenities via Overpass API.
    """
    user = await user_repo.get_user_by_clerk_id(clerk_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with the specified Clerk ID not found."
        )
    data = {
        "seller_id": user.id,
        "title": property_data.title,
        "description": property_data.description,
        "price": property_data.price,
        "property_type": (property_data.property_type or "").lower(),
        "area_sqft": property_data.area_sqft,
        "bedrooms": property_data.bedrooms,
        "bathrooms": property_data.bathrooms,
        "floors": property_data.floors or 1,
        "city": property_data.city,
        "area": property_data.area,
        "lng": property_data.lng,
        "lat": property_data.lat,
        "images": property_data.images or [],
        "metadata": property_data.metadata or {},
        "external_id": property_data.external_id,
        "source": property_data.source,
        "source_url": property_data.source_url,
        "date_added": property_data.date_added,
    }
    row = await property_repo.create(data)
    embedding = embed_text(compose_property_text(property_repo._row_to_dict(row)))
    try:
        await upsert_property_embedding(
            property_id=row.id,
            embedding=embedding,
            metadata={
                "title": row.title,
                "city": row.city,
                "area": row.area,
                "property_type": row.property_type,
                "bedrooms": row.bedrooms,
                "bathrooms": row.bathrooms,
                "price": row.price,
            },
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to upsert property embedding to Qdrant: %s", e)

    # Schedule background task for amenity enrichment (fetches from Overpass, generates summary via Groq, updates Qdrant)
    if row.lat is not None and row.lng is not None:
        from services.amenities.service import enrich_property_amenities
        import asyncio

        async def _run_amenity_enrichment():
            await enrich_property_amenities(
                property_id=row.id,
                lat=row.lat,
                lon=row.lng,
                city=row.city,
                area=row.area,
            )

        background_tasks.add_task(asyncio.run, _run_amenity_enrichment())

    return property_repo._row_to_dict(row)


@router.delete("/{property_id}", summary="Delete a property listing")
async def delete_property(
    property_id: str,
    clerk_id: str = Query(..., description="Clerk user ID"),
    user_repo: UserRepository = Depends(get_user_repository),
    property_repo: PropertyRepository = Depends(get_property_repository),
):
    """
    Deletes a property listing. Only the owner (seller) can delete their own property.
    Also removes the property from Qdrant vector search.
    """
    pid = parse_uuid(property_id, "property_id")
    user = await user_repo.get_user_by_clerk_id(clerk_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with the specified Clerk ID not found."
        )
    doc = await property_repo.get_by_id(pid)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    if doc["seller_id"] != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this property"
        )
    deleted = await property_repo.delete(pid)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete property"
        )
    try:
        await delete_embedding(collection_name=PROPERTIES_COLLECTION, point_id=pid)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to delete property embedding from Qdrant: %s", e)
    return {"success": True, "message": "Property deleted successfully"}


@router.post("/generate-description", summary="Generate property description using LLM")
async def generate_description(
    property_data: Dict[str, Any] = Body(...),
    clerk_id: str = Query(..., description="Clerk user ID"),
):
    """
    Generates a property description using LLM based on provided property details.
    """
    try:
        description = _generate_description_with_llm(property_data)
        return {"description": description}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate description: {str(e)}"
        )


@router.post("/transcribe-audio", summary="Transcribe audio file to text using Groq Whisper")
async def transcribe_audio(
    audio_file: UploadFile = File(...),
    clerk_id: str = Query(..., description="Clerk user ID"),
):
    """
    Transcribes an audio file to text using Groq's Whisper API.
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
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transcribe audio: {str(e)}"
        )


@router.post("/{property_id}/contact-seller", summary="Contact seller for a property (requires authentication)")
async def contact_seller(
    property_id: str,
    request: Request,
    message: Optional[str] = Body(None, description="Optional message to seller"),
    current_user: User = Depends(get_current_user),
    property_repo: PropertyRepository = Depends(get_property_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """
    Contact the seller of a property. Requires authentication.
    Returns seller contact information and initiates a contact request.
    """
    # Validate property ID
    pid = parse_uuid(property_id, "property_id")
    
    # Get property
    property_doc = await property_repo.get_by_id(pid)
    if not property_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )
    
    # Get seller information
    seller_id = property_doc.get("seller_id")
    if not seller_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Property seller information not available"
        )
    
    seller = await user_repo.get_by_id(seller_id)
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seller not found"
        )
    
    # Prevent users from contacting themselves
    if current_user.id == seller_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot contact yourself"
        )
    
    # Return seller contact information (limited for privacy)
    return {
        "success": True,
        "message": "Contact request initiated successfully",
        "property": {
            "id": property_doc.get("id"),
            "title": property_doc.get("title"),
        },
        "seller": {
            "id": seller.id,
            "name": seller.name,
            "email": seller.email if seller.email else None,
            "phone": seller.phone if seller.phone else None,
        },
        "buyer": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
        },
        "contact_message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }



