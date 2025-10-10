"""
Builder bids models (for project bidding)
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from .base import PyObjectId


class BuilderBidBase(BaseModel):
    """Base builder bid model"""

    proposal_title: str = Field(..., min_length=1, max_length=200)
    proposal_details: str
    estimated_cost: float = Field(..., gt=0)
    estimated_duration: str
    attachments: List[str] = Field(
        default=[], description="Array of URLs (designs, PDFs, etc.)"
    )
    status: str = Field(
        default="pending",
        description="pending, shortlisted, rejected, accepted",
    )


class BuilderBid(BuilderBidBase):
    """Complete builder bid model"""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    project_id: PyObjectId
    builder_id: PyObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class BuilderBidCreate(BuilderBidBase):
    """Schema for creating builder bid"""

    project_id: PyObjectId


class BuilderBidResponse(BuilderBidBase):
    """Schema for builder bid API responses"""

    id: PyObjectId = Field(alias="_id")
    project_id: PyObjectId
    builder_id: PyObjectId
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

