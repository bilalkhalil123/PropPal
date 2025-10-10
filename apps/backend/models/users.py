"""
User models for authentication and user management
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from .base import PyObjectId


class UserBase(BaseModel):
    """Base user model with common fields"""

    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    role: str = Field(..., description="User role: buyer, seller, builder, admin")
    profile_image: Optional[str] = None


class User(UserBase):
    """Complete user model (for internal use)"""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+92-300-1234567",
                "role": "buyer",
                "profile_image": "https://example.com/profile.jpg",
                "password_hash": "$2b$12$...",
                "created_at": "2025-10-09T12:00:00",
                "updated_at": "2025-10-09T12:00:00",
            }
        },
    )


class UserCreate(UserBase):
    """Schema for creating a new user"""

    password: str = Field(..., min_length=8, max_length=100)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+92-300-1234567",
                "role": "buyer",
                "password": "securepassword123",
            }
        }
    )


class UserResponse(UserBase):
    """Schema for user API responses (excludes password_hash)"""

    id: PyObjectId = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+92-300-1234567",
                "role": "buyer",
                "profile_image": "https://example.com/profile.jpg",
                "created_at": "2025-10-09T12:00:00",
                "updated_at": "2025-10-09T12:00:00",
            }
        },
    )

