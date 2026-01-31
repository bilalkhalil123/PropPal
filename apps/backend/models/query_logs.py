"""
Query logs models (for NLP/RAG system)
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class QueryLogBase(BaseModel):
    """Base query log model"""

    query_text: str
    query_embedding: Optional[str] = Field(
        None, description="Vector embedding as string"
    )
    intent: Optional[str] = Field(None, description="Detected user intent")
    result_refs: Optional[str] = Field(
        None, description="References to results (JSON array)"
    )


class QueryLog(QueryLogBase):
    """Complete query log model (id and user_id are UUID strings)."""

    id: str = Field(..., alias="_id")
    user_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class QueryLogCreate(QueryLogBase):
    """Schema for creating query log"""

    user_id: Optional[str] = None


class QueryLogResponse(QueryLogBase):
    """Schema for query log API responses (id and user_id are UUID strings)."""

    id: str = Field(..., alias="_id")
    user_id: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

