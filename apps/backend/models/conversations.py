"""
Conversation models (buyer <-> builder direct chat).
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class ConversationBase(BaseModel):
    conversation_type: str = Field(default="direct", description="direct, project_inquiry, bid_discussion")
    project_id: Optional[str] = None
    bid_id: Optional[str] = None


class ConversationCreate(ConversationBase):
    participant_ids: List[str]
    initial_message: Optional[str] = None


class ConversationResponse(ConversationBase):
    id: str = Field(..., alias="_id")
    participant_ids: List[str]
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class ConversationMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class ConversationMessageResponse(BaseModel):
    id: str = Field(..., alias="_id")
    conversation_id: str
    sender_id: str
    content: str
    created_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
