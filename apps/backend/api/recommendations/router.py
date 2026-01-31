"""
Property recommendations API.
Uses PostgreSQL (ChatHistoryRepository, PropertyRepository); user_id is UUID string.
"""
from fastapi import APIRouter, Depends, Query, HTTPException

from common.repositories.chat_history_repository import ChatHistoryRepository, get_chat_history_repository
from common.repositories.property_repository import PropertyRepository, get_property_repository
from common.uuid_utils import parse_uuid
from services.recommendations.property_recommendations import get_recommended_properties, get_popular_properties

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("/properties")
async def get_property_recommendations(
    user_id: str = Query("", description="User ID (UUID). Empty string returns popular properties."),
    limit: int = Query(12, ge=1, le=50, description="Maximum number of recommendations"),
    days_back: int = Query(30, ge=1, le=365, description="Days of history to analyze"),
    chat_repo: ChatHistoryRepository = Depends(get_chat_history_repository),
    property_repo: PropertyRepository = Depends(get_property_repository),
):
    """
    Get personalized property recommendations based on user's recent searches.
    If user_id is empty, returns popular properties. Otherwise user_id must be a valid UUID (404 if invalid).
    """
    if not user_id or user_id.strip() == "":
        return await get_popular_properties(property_repo, limit)

    try:
        parse_uuid(user_id, "user_id")
    except HTTPException:
        raise

    try:
        return await get_recommended_properties(
            user_id=user_id.strip(),
            chat_repo=chat_repo,
            property_repo=property_repo,
            limit=limit,
            days_back=days_back,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")

