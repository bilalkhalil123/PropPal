"""
Visit booking models
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class VisitBase(BaseModel):
    """Base visit model"""

    proposed_time_slots: List[str] = Field(
        default=[], description="Array of ISO timestamp strings"
    )
    confirmed_time: Optional[datetime] = None
    status: str = Field(
        default="pending",
        description="pending, confirmed, cancelled, completed, rescheduled",
    )
    agent_notes: Optional[str] = None
    seller_id: Optional[str] = None
    cancelled_by: Optional[str] = None
    cancellation_reason: Optional[str] = None


class Visit(VisitBase):
    """Complete visit model (id and FKs are UUID strings)."""

    id: str = Field(..., alias="_id")
    buyer_id: str
    property_id: Optional[str] = None
    builder_id: Optional[str] = Field(
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

    property_id: Optional[str] = None
    builder_id: Optional[str] = None


class VisitResponse(VisitBase):
    """Schema for visit API responses (id and FKs are UUID strings)."""

    id: str = Field(..., alias="_id")
    buyer_id: str
    property_id: Optional[str] = None
    builder_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

