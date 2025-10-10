"""
Chat history models
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from .base import PyObjectId


class ChatMessage(BaseModel):
    """Single chat message"""

    role: str = Field(..., description="user or assistant")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatHistoryBase(BaseModel):
    """Base chat history model"""

    messages: List[ChatMessage] = Field(default=[], description="Array of messages")


class ChatHistory(ChatHistoryBase):
    """Complete chat history model"""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class ChatHistoryCreate(ChatHistoryBase):
    """Schema for creating chat history"""

    pass


class ChatHistoryResponse(ChatHistoryBase):
    """Schema for chat history API responses"""

    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

