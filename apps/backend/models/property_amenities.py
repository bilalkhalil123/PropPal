"""
Property amenities models (schools, hospitals, nearby facilities)
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class PropertyAmenityBase(BaseModel):
    """Base amenity model"""

    name: str
    type: str = Field(..., description="school, hospital, park, etc.")
    rating: Optional[float] = Field(None, ge=0, le=5)
    distance_meters: float = Field(..., ge=0)
    duration_minutes: Optional[float] = Field(None, ge=0)
    location_name: str
    lat: float
    lng: float
    external_id: Optional[str] = None


class PropertyAmenity(PropertyAmenityBase):
    """Complete property amenity model (id and property_id are UUID strings)."""

    id: str = Field(..., alias="_id")
    property_id: str
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class PropertyAmenityCreate(PropertyAmenityBase):
    """Schema for creating property amenity"""

    property_id: str


class PropertyAmenityResponse(PropertyAmenityBase):
    """Schema for amenity API responses (id and property_id are UUID strings)."""

    id: str = Field(..., alias="_id")
    property_id: str
    fetched_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

