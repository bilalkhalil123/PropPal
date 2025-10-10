"""
User projects models (for builder bidding system)
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from .base import PyObjectId


class UserProjectBase(BaseModel):
    """Base user project model"""

    title: str = Field(..., min_length=1, max_length=200)
    description: str
    project_type: str = Field(..., description="construction, renovation, etc.")
    budget_min: float = Field(..., gt=0)
    budget_max: float = Field(..., gt=0)
    location: str
    status: str = Field(
        default="open", description="open, in_discussion, closed"
    )


class UserProject(UserProjectBase):
    """Complete user project model"""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    property_id: Optional[PyObjectId] = Field(
        None, description="Can be null if not linked to a property"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class UserProjectCreate(UserProjectBase):
    """Schema for creating user project"""

    property_id: Optional[PyObjectId] = None


class UserProjectResponse(UserProjectBase):
    """Schema for user project API responses"""

    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    property_id: Optional[PyObjectId] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

