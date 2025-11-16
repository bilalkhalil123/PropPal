"""
Builder services models
"""
from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from .base import PyObjectId


class BuilderServiceBase(BaseModel):
    """Base builder service model"""

    title: str = Field(..., min_length=1, max_length=200)
    description: str
    category: str = Field(..., description="renovation, architecture, construction, etc.")
    base_price: float = Field(..., gt=0)
    price_unit: str = Field(..., description="per sqft, fixed, per hour, etc.")
    estimated_duration: Optional[str] = None
    service_features: List[str] = Field(
        default=[], description="List of features: 3D design, material sourcing, etc."
    )


class BuilderService(BuilderServiceBase):
    """Complete builder service model"""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    builder_id: PyObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    embeddings: Optional[List[float]] = Field(
        default=None, description="Vector embeddings for the builder service"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class BuilderServiceCreate(BuilderServiceBase):
    """Schema for creating builder service"""

    pass


class BuilderServiceResponse(BuilderServiceBase):
    """Schema for builder service API responses"""

    id: PyObjectId = Field(alias="_id")
    builder_id: PyObjectId
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

