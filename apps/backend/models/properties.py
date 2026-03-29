"""
Property listing models
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


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
    lng: Optional[float] = Field(default=None, description="Longitude")
    lat: Optional[float] = Field(default=None, description="Latitude")


class Property(PropertyBase):
    """Complete property model (id and seller_id are UUID strings)."""

    id: str = Field(..., alias="_id")
    seller_id: str
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


class PropertyCreateRequest(PropertyBase):
    """Schema for creating a new property listing via API (seller_id derived from clerk_id)"""

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


class PropertyCreate(PropertyBase):
    """Schema for creating a new property listing (internal use, includes seller_id)"""

    seller_id: str
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
    """Schema for property API responses (id and seller_id are UUID strings)."""

    id: str = Field(..., alias="_id")
    seller_id: str
    images: List[str] = Field(default=[])
    metadata: dict = Field(default={})
    external_id: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    date_added: Optional[datetime] = None
    last_indexed_at: Optional[datetime] = None
    nearby_amenities: Optional[dict] = Field(default=None, description="Raw nearby amenities JSON from Overpass API")
    amenity_summary: Optional[str] = Field(default=None, description="Groq-generated human-readable amenity summary")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

