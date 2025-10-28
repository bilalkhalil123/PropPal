"""
Chat API with RouterAgent integration.
Provides conversational interface using the RouterAgent orchestrator.
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents import RouterAgent
from common.db import get_database
from common.repositories.user_repository import UserRepository, get_user_repository
from bson import ObjectId
from datetime import datetime

# Initialize the router
router = APIRouter(prefix="/api/chat", tags=["chat"])

def get_router_agent():
    """Create a fresh RouterAgent instance for each request to avoid state issues."""
    # Always create a fresh instance to prevent state persistence issues
    return RouterAgent()


# --- Request/Response Models ---

class ChatRequest(BaseModel):
    """Request model for chat messages."""
    message: str = Field(..., description="The user's message/query", min_length=1, max_length=1000)
    user_id: Optional[str] = Field(None, description="Optional internal DB user ID for session tracking")
    clerk_id: Optional[str] = Field(None, description="Optional Clerk user ID for resolving internal user id")
    session_id: Optional[str] = Field(None, description="Optional session ID for conversation context")


class ChatResponse(BaseModel):
    """Response model for chat messages."""
    success: bool = Field(..., description="Whether the request was successful")
    response: str = Field(..., description="The agent's response message")
    classification: str = Field(..., description="The classification of the query (listing_agent, general_chat, etc.)")
    error: Optional[str] = Field(None, description="Error message if any")
    properties: Optional[List[Dict[str, Any]]] = Field(None, description="Properties search results")
    builders: Optional[List[Dict[str, Any]]] = Field(None, description="Builder search results")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata about the response")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    agent_name: str = Field(..., description="Name of the active agent")
    version: str = Field(..., description="API version")


# --- API Endpoints ---

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify the chat service is running.
    """
    agent = get_router_agent()
    return HealthResponse(
        status="healthy",
        agent_name=agent.name,
        version="1.0.0"
    )


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """
    Send a message to the chat agent and get a response.
    
    This endpoint uses the RouterAgent to intelligently route queries to the appropriate
    specialized agent (e.g., ListingAgent for property searches, general chat for other queries).
    
    Args:
        request: ChatRequest containing the user's message and optional metadata
        
    Returns:
        ChatResponse with the agent's response and classification
    """
    try:
        # Validate input
        if not request.message or not request.message.strip():
            raise HTTPException(
                status_code=400,
                detail="Message cannot be empty"
            )
        
        # Process the query through the RouterAgent
        agent = get_router_agent()
        result = agent.process_query(request.message.strip())
        
        # Check if the agent processing was successful
        if not result.get("success", False):
            raise HTTPException(
                status_code=500,
                detail=f"Agent processing failed: {result.get('error', 'Unknown error')}"
            )
        
        # Resolve internal user id from clerk_id if provided
        resolved_user_id: Optional[str] = None
        if request.clerk_id:
            try:
                user = await user_repo.get_user_by_clerk_id(request.clerk_id)
                if user and getattr(user, "id", None):
                    resolved_user_id = str(user.id)
            except Exception:
                resolved_user_id = None
        if not resolved_user_id and request.user_id:
            resolved_user_id = request.user_id

        # Prepare metadata
        metadata = {
            "user_id": resolved_user_id,
            "session_id": request.session_id,
            "clerk_id": request.clerk_id,
            "query_length": len(request.message),
            "agent_type": result.get("classification", "unknown")
        }

        # --- Persist chat history per (user_id, session_id) document ---
        try:
            if resolved_user_id and request.session_id:
                history_key: Any = ObjectId(resolved_user_id) if ObjectId.is_valid(resolved_user_id) else resolved_user_id
                now = datetime.utcnow()
                user_msg = {"role": "user", "content": request.message.strip(), "timestamp": now}
                ai_msg = {
                    "role": "assistant",
                    "content": result.get("response", ""),
                    "timestamp": now,
                    "_payload": {
                        "classification": result.get("classification"),
                        "properties": result.get("properties"),
                        "builders": result.get("builders"),
                    },
                }

                await db["chat_histories"].update_one(
                    {"user_id": history_key, "session_id": request.session_id},
                    {
                        "$setOnInsert": {"created_at": now, "session_id": request.session_id},
                        "$set": {"updated_at": now},
                        "$push": {"messages": {"$each": [user_msg, ai_msg]}},
                    },
                    upsert=True,
                )
        except Exception:
            # Do not fail the chat if logging encounters an error
            pass
        
        # Return the response with properties and builders
        return ChatResponse(
            success=True,
            response=result.get("response", "No response generated"),
            classification=result.get("classification", "unknown"),
            properties=result.get("properties"),
            builders=result.get("builders"),
            error=None,
            metadata=metadata
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/conversation", response_model=ChatResponse)
async def start_conversation(request: ChatRequest, db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Start a new conversation with the chat agent.
    
    This is an alias for the /message endpoint but with a more conversational name.
    Useful for frontend applications that want to distinguish between single messages
    and conversation starters.
    """
    return await send_message(request, db)


# --- Additional Utility Endpoints ---

@router.get("/capabilities")
async def get_capabilities():
    """
    Get information about what the chat agent can do.
    """
    return {
        "capabilities": [
            "Property search and real estate queries",
            "General conversation and platform help",
            "Intelligent query classification and routing",
            "Multi-agent orchestration"
        ],
        "supported_queries": [
            "Property searches (e.g., 'Find houses in Islamabad')",
            "General questions (e.g., 'What is PropPal?')",
            "Platform help (e.g., 'How do I create an account?')",
            "Mixed queries (e.g., 'Hi, I need help with property search')"
        ],
        "agents": {
            "listing_agent": "Handles property searches and real estate queries",
            "general_chat": "Handles general conversation and platform help"
        }
    }


@router.get("/status")
async def get_status():
    """
    Get detailed status information about the chat service.
    """
    try:
        # Test the agent with a simple query
        agent = get_router_agent()
        test_result = agent.process_query("Hello")
        
        return {
            "status": "operational" if test_result.get("success") else "degraded",
            "agent_name": agent.name,
            "last_test": {
                "query": "Hello",
                "success": test_result.get("success"),
                "classification": test_result.get("classification"),
                "response_length": len(test_result.get("response", ""))
            },
            "timestamp": "2024-01-01T00:00:00Z"  # You might want to use actual timestamp
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "agent_name": "RouterAgent"
        }


# =============================
# Read endpoints for chat logs
# =============================

def _str_oid(value: Any) -> Any:
    try:
        if isinstance(value, ObjectId):
            return str(value)
    except Exception:
        pass
    return value

def _normalize_messages(msgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for m in msgs:
        mm = {k: _str_oid(v) for k, v in m.items()}
        # ensure timestamp is ISO string
        ts = mm.get("timestamp")
        if isinstance(ts, datetime):
            mm["timestamp"] = ts.isoformat()
        out.append(mm)
    return out


@router.get("/history")
async def get_chat_history(
    user_id: str = Query(..., description="User id (Mongo ObjectId, external, or 'session:<sid>')"),
    session_id: Optional[str] = Query(None, description="Filter messages by session id (optional)"),
    limit: int = Query(50, ge=1, le=200, description="Max messages to return (newest last)"),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Return a user's chat history. If session_id is provided, messages are filtered to that session.
    Messages are returned ascending by time and capped by limit (last N).
    """
    query_id: Any = user_id
    if user_id.startswith("session:"):
        query_id = user_id
    elif ObjectId.is_valid(user_id):
        query_id = ObjectId(user_id)

    doc = await db["chat_histories"].find_one({"user_id": query_id})
    if not doc:
        return {"count": 0, "messages": []}

    messages: List[Dict[str, Any]] = doc.get("messages", [])
    if session_id:
        messages = [m for m in messages if m.get("_payload", {}).get("session_id") == session_id]

    # sort by timestamp ascending
    def _get_ts(m: Dict[str, Any]) -> float:
        ts = m.get("timestamp")
        if isinstance(ts, datetime):
            return ts.timestamp()
        try:
            return datetime.fromisoformat(ts).timestamp()
        except Exception:
            return 0.0

    messages.sort(key=_get_ts)
    if len(messages) > limit:
        messages = messages[-limit:]

    return {
        "count": len(messages),
        "messages": _normalize_messages(messages),
        "updated_at": (doc.get("updated_at").isoformat() if isinstance(doc.get("updated_at"), datetime) else doc.get("updated_at")),
        "_id": _str_oid(doc.get("_id")),
    }


@router.get("/history/messages")
async def get_chat_messages_paginated(
    user_id: str = Query(..., description="User id (Mongo ObjectId, external, or 'session:<sid>')"),
    session_id: Optional[str] = Query(None),
    before_ms: Optional[int] = Query(None, description="Return messages older than this epoch ms"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Cursor-style pagination for messages (newest to oldest).
    Pass before_ms to page older messages. Returns nextBeforeMs if more exist.
    """
    query_id: Any = user_id
    if user_id.startswith("session:"):
        query_id = user_id
    elif ObjectId.is_valid(user_id):
        query_id = ObjectId(user_id)

    doc = await db["chat_histories"].find_one({"user_id": query_id})
    if not doc:
        return {"count": 0, "messages": [], "nextBeforeMs": None}

    messages: List[Dict[str, Any]] = doc.get("messages", [])
    if session_id:
        messages = [m for m in messages if m.get("_payload", {}).get("session_id") == session_id]

    # to newest-first order
    def _ts(m: Dict[str, Any]) -> float:
        t = m.get("timestamp")
        if isinstance(t, datetime):
            return t.timestamp()
        try:
            return datetime.fromisoformat(t).timestamp()
        except Exception:
            return 0.0

    messages.sort(key=_ts, reverse=True)

    if before_ms is not None:
        messages = [m for m in messages if _ts(m) * 1000 < before_ms]

    page = messages[:limit]
    next_before = int(_ts(page[-1]) * 1000) if len(page) == limit else None

    # Return ascending for rendering if preferred by client; keep newest-last here
    page.reverse()
    return {
        "count": len(page),
        "messages": _normalize_messages(page),
        "nextBeforeMs": next_before,
    }


@router.get("/sessions")
async def list_chat_sessions(
    user_id: str = Query(..., description="User id (Mongo ObjectId, external, or 'session:<sid>')"),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Return a condensed list of prior sessions (by session_id) with last message and updated time.
    This derives sessions from the _payload.session_id embedded in messages.
    """
    query_id: Any = user_id
    if user_id.startswith("session:"):
        query_id = user_id
    elif ObjectId.is_valid(user_id):
        query_id = ObjectId(user_id)

    doc = await db["chat_histories"].find_one({"user_id": query_id})
    if not doc:
        return {"count": 0, "sessions": []}

    sessions: Dict[str, Dict[str, Any]] = {}
    for m in doc.get("messages", []):
        payload = m.get("_payload") or {}
        sid = payload.get("session_id") or "default"
        ts = m.get("timestamp")
        ts_val = ts.isoformat() if isinstance(ts, datetime) else ts
        entry = sessions.get(sid) or {"session_id": sid, "last_message": "", "updated_at": ts_val}
        # prefer assistant text or user text as preview
        preview = m.get("content") or ""
        entry["last_message"] = preview[:120]
        entry["updated_at"] = ts_val
        sessions[sid] = entry

    # sort by updated_at desc
    def _ts_iso(v: str) -> float:
        try:
            return datetime.fromisoformat(v).timestamp()
        except Exception:
            return 0.0

    items = list(sessions.values())
    items.sort(key=lambda x: _ts_iso(x.get("updated_at") or ""), reverse=True)
    return {"count": len(items), "sessions": items}
