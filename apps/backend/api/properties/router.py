from __future__ import annotations

from typing import Any, Dict, Union, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, UploadFile, File
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
import tempfile
import os

# Ensure common module import
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.db import get_database
from models.properties import PropertyCreate, PropertyCreateRequest
from agents.listing.tools.property_creation import create_property_sync
from agents.listing.create_listing_agent import _generate_description_with_llm
from services.vector_search.qdrant_service import delete_embedding
from common.qdrant import PROPERTIES_COLLECTION


router = APIRouter(prefix="/api/properties", tags=["properties"])


def _normalize(value: Union[Dict[str, Any], List[Any], Any]) -> Union[Dict[str, Any], List[Any], Any]:
    """Recursively convert ObjectId instances to strings in any structure."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    return value


@router.get("/{property_id}", summary="Get full property details by ID")
async def get_property_by_id(
    property_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Fetches a single property document from MongoDB by its ObjectId.
    """
    try:
        _id = ObjectId(property_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid property id"
        )

    # Exclude large/unnecessary fields for payload size and cleanliness
    projection = {
        "embeddings": 0,
        "source": 0,
        "metadata.raw": 0,
        "metadata.external_id": 0,
    }
    doc = await db["properties"].find_one({"_id": _id}, projection)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    return _normalize(doc)


@router.get("", summary="Get properties by seller (clerk_id)")
async def get_properties_by_seller(
    clerk_id: str = Query(..., description="Clerk user ID"),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Fetches all properties listed by a specific seller (identified by clerk_id).
    """
    try:
        # Find user by clerk_id
        user = await db["users"].find_one({"clerk_id": clerk_id}, {"_id": 1})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with the specified Clerk ID not found."
            )
        
        seller_id = user["_id"]
        
        # Find all properties by this seller
        # Exclude large/unnecessary fields
        projection = {
            "embeddings": 0,
            "source": 0,
            "metadata.raw": 0,
            "metadata.external_id": 0,
        }
        
        cursor = db["properties"].find({"seller_id": seller_id}, projection).sort("created_at", -1)
        properties = await cursor.to_list(length=100)  # Limit to 100 properties
        
        return [_normalize(prop) for prop in properties]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching properties: {str(e)}"
        )


@router.post("", summary="Create a new property listing")
async def create_property(
    property_data: PropertyCreateRequest,
    clerk_id: str = Query(..., description="Clerk user ID"),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Creates a new property listing in the database.
    Requires all property fields to be provided.
    The seller_id is automatically derived from the clerk_id.
    """
    try:
        # Validate clerk_id and get user
        user = await db["users"].find_one({"clerk_id": clerk_id}, {"_id": 1})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with the specified Clerk ID not found."
            )
        
        seller_id = user["_id"]
        
        # Create property using the creation tool
        result = create_property_sync(
            clerk_id=clerk_id,
            title=property_data.title,
            description=property_data.description,
            price=property_data.price,
            property_type=property_data.property_type,
            area_sqft=property_data.area_sqft,
            bedrooms=property_data.bedrooms,
            bathrooms=property_data.bathrooms,
            floors=property_data.floors or 1,
            city=property_data.city,
            area=property_data.area,
            lng=property_data.lng,
            lat=property_data.lat,
            images=property_data.images or [],
            metadata=property_data.metadata or {},
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to create property")
            )
        
        # Fetch the created property
        property_id = ObjectId(result.get("property_id"))
        created_property = await db["properties"].find_one({"_id": property_id})
        
        if not created_property:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Property was created but could not be retrieved"
            )
        
        return _normalize(created_property)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the property: {str(e)}"
        )


@router.delete("/{property_id}", summary="Delete a property listing")
async def delete_property(
    property_id: str,
    clerk_id: str = Query(..., description="Clerk user ID"),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Deletes a property listing. Only the owner (seller) can delete their own property.
    Also removes the property from Qdrant vector search.
    """
    try:
        # Validate property_id
        try:
            _id = ObjectId(property_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid property id"
            )
        
        # Find user by clerk_id
        user = await db["users"].find_one({"clerk_id": clerk_id}, {"_id": 1})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with the specified Clerk ID not found."
            )
        
        seller_id = user["_id"]
        
        # Find the property and verify ownership
        property_doc = await db["properties"].find_one({"_id": _id})
        if not property_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )
        
        # Verify the property belongs to this seller
        if property_doc.get("seller_id") != seller_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this property"
            )
        
        # Delete from MongoDB
        delete_result = await db["properties"].delete_one({"_id": _id})
        
        if delete_result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete property"
            )
        
        # Delete from Qdrant
        try:
            await delete_embedding(collection_name=PROPERTIES_COLLECTION, point_id=property_id)
        except Exception as e:
            # Log but don't fail if Qdrant deletion fails
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to delete property embedding from Qdrant: {e}")
        
        return {"success": True, "message": "Property deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting the property: {str(e)}"
        )


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



