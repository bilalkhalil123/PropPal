"""
Builder profile models
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from .base import PyObjectId


class BuilderProfileBase(BaseModel):
    """Base builder profile model"""

    company_name: str = Field(..., min_length=1, max_length=200)
    specialization: List[str] = Field(
        default=[],
        description="List of specializations: construction, renovation, interior, etc.",
    )
    experience_years: int = Field(..., ge=0)
    portfolio_images: Optional[str] = Field(None, description="JSON array of image URLs")
    rating: Optional[float] = Field(None, ge=0, le=5)
    about: Optional[str] = None


class BuilderProfile(BuilderProfileBase):
    """Complete builder profile model"""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class BuilderProfileCreate(BuilderProfileBase):
    """Schema for creating builder profile"""

    pass


class BuilderProfileResponse(BuilderProfileBase):
    """Schema for builder profile API responses"""

    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

