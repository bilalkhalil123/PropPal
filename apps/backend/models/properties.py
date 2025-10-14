"""
Property listing models
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from .base import PyObjectId


class PropertyBase(BaseModel):
    """Base property model with common fields"""

    title: str = Field(..., min_length=1, max_length=200)
    description: str
    price: float = Field(..., gt=0)
    property_type: str = Field(..., description="house, apartment, plot, commercial, etc.")
    area_sqft: float = Field(..., gt=0)
    bedrooms: int = Field(..., ge=0)
    bathrooms: int = Field(..., ge=0)
    floors: int = Field(default=1, ge=1)
    city: str
    area: str
    lng: float = Field(..., description="Longitude")
    lat: float = Field(..., description="Latitude")


class Property(PropertyBase):
    """Complete property model"""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    seller_id: PyObjectId
    images: Optional[List[str]] = Field(
        default=None, description="Array of image URLs"
    )
    embedding: Optional[List[float]] = Field(None, description="Vector embedding (float array)")
    metadata: Optional[str] = Field(None, description="Additional metadata as JSON")
    # Provenance fields for external listings (e.g., Zameen)
    external_id: Optional[str] = Field(default=None, description="External listing ID")
    source: Optional[str] = Field(default=None, description='Source system, e.g., "zameen"')
    source_url: Optional[str] = Field(default=None, description="Source listing URL")
    date_added: Optional[datetime] = Field(default=None, description="Original date added")
    last_indexed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class PropertyCreate(PropertyBase):
    """Schema for creating a new property listing"""

    seller_id: PyObjectId
    images: Optional[List[str]] = Field(default=[], description="Array of image URLs")
    metadata: Optional[dict] = Field(default={}, description="Additional metadata")
    # Optional provenance inputs on create (useful for imports)
    external_id: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    date_added: Optional[datetime] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Beautiful 3-Bedroom House in F-10",
                "description": "Spacious house with modern amenities",
                "price": 15000000,
                "property_type": "house",
                "area_sqft": 2500,
                "bedrooms": 3,
                "bathrooms": 3,
                "floors": 2,
                "city": "Islamabad",
                "area": "F-10/3",
                "lng": 73.0479,
                "lat": 33.6844,
                "images": ["https://example.com/img1.jpg"],
            }
        }
    )


class PropertyResponse(PropertyBase):
    """Schema for property API responses"""

    id: PyObjectId = Field(alias="_id")
    seller_id: PyObjectId
    images: List[str] = Field(default=[])
    metadata: dict = Field(default={})
    external_id: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    date_added: Optional[datetime] = None
    last_indexed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

