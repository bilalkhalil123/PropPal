"""
User projects models (for builder bidding system)
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


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
    """Complete user project model (id, user_id, property_id are UUID strings)."""

    id: str = Field(..., alias="_id")
    user_id: str
    property_id: Optional[str] = Field(
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

    property_id: Optional[str] = None


class UserProjectResponse(UserProjectBase):
    """Schema for user project API responses (id, user_id, property_id are UUID strings)."""

    id: str = Field(..., alias="_id")
    user_id: str
    property_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

