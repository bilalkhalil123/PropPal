"""
Property recommendations API.

Provides personalized property recommendations based on user's chat history.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.db import get_database
from services.recommendations.property_recommendations import get_recommended_properties, get_popular_properties

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("/properties")
async def get_property_recommendations(
    user_id: str = Query("", description="User ID (MongoDB ObjectId). Empty string returns popular properties."),
    limit: int = Query(12, ge=1, le=50, description="Maximum number of recommendations"),
    days_back: int = Query(30, ge=1, le=365, description="Days of history to analyze"),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Get personalized property recommendations based on user's recent searches.
    
    This endpoint analyzes the user's chat history to extract property search patterns
    and returns properties similar to what they've been searching for.
    
    If user_id is empty, returns popular properties immediately (fast).
    
    Args:
        user_id: User's MongoDB ObjectId (optional - empty string returns popular properties)
        limit: Maximum number of recommendations (default: 12)
        days_back: How many days of history to analyze (default: 30)
        
    Returns:
        Dictionary with:
            - properties: List of recommended properties
            - count: Number of properties returned
            - source: "recent_searches" or "popular" (fallback)
    """
    # If no user_id, return popular properties immediately (fast)
    if not user_id or user_id.strip() == "":
        return await get_popular_properties(db, limit)
    
    try:
        result = await get_recommended_properties(
            user_id=user_id,
            db=db,
            limit=limit,
            days_back=days_back,
        )
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating recommendations: {str(e)}"
        )

