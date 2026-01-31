"""
Builder project showcase models
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ProjectBase(BaseModel):
    """Base project model"""

    title: str = Field(..., min_length=1, max_length=200)
    description: str
    status: str = Field(..., description="completed, ongoing, planned, etc.")
    images: List[str] = Field(default=[], description="Array of image URLs")
    location: str


class Project(ProjectBase):
    """Complete project model (id and builder_id are UUID strings)."""

    id: str = Field(..., alias="_id")
    builder_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class ProjectCreate(ProjectBase):
    """Schema for creating project"""

    pass


class ProjectResponse(ProjectBase):
    """Schema for project API responses (id and builder_id are UUID strings)."""

    id: str = Field(..., alias="_id")
    builder_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

