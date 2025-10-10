"""
Visit booking models
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from .base import PyObjectId


class VisitBase(BaseModel):
    """Base visit model"""

    proposed_time_slots: List[str] = Field(
        default=[], description="Array of ISO timestamp strings"
    )
    confirmed_time: Optional[datetime] = None
    status: str = Field(
        default="pending",
        description="pending, confirmed, cancelled, completed",
    )
    agent_notes: Optional[str] = None


class Visit(VisitBase):
    """Complete visit model"""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    buyer_id: PyObjectId
    property_id: Optional[PyObjectId] = None
    builder_id: Optional[PyObjectId] = Field(
        None, description="For direct builder appointments"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class VisitCreate(VisitBase):
    """Schema for creating visit"""

    property_id: Optional[PyObjectId] = None
    builder_id: Optional[PyObjectId] = None


class VisitResponse(VisitBase):
    """Schema for visit API responses"""

    id: PyObjectId = Field(alias="_id")
    buyer_id: PyObjectId
    property_id: Optional[PyObjectId] = None
    builder_id: Optional[PyObjectId] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

