"""
Chat API with RouterAgent integration.
Provides conversational interface using the RouterAgent orchestrator.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, status, UploadFile, File, Form
from pydantic import BaseModel, Field
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents import RouterAgent
from agents.builder.create_service_agent import BuilderServiceCreationAgent
from agents.builder.create_profile_agent import BuilderProfileCreationAgent
from agents.listing.agent import ListingAgent
from common.db import get_db_session_ctx
from common.repositories.user_repository import UserRepository, get_user_repository
from common.repositories.chat_history_repository import ChatHistoryRepository, get_chat_history_repository
from common.uuid_utils import parse_uuid
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
import json
import logging

from services.asr.language import detect_language
from services.asr.translation import translate_to_english, translate_to_urdu
from services.asr.service import transcribe_audio_bytes

logger = logging.getLogger(__name__)

# Initialize the router
router = APIRouter(prefix="/api/chat", tags=["chat"])

def get_router_agent():
    """Create a fresh RouterAgent instance for each request to avoid state issues."""
    # Always create a fresh instance to prevent state persistence issues
    return RouterAgent()


def _normalize_user_message(message: str, language_hint: Optional[str] = None) -> tuple[str, Dict[str, Any]]:
    normalized = (message or "").strip()
    if not normalized:
        return "", {"input_language": language_hint or "unknown"}

    input_language = (language_hint or detect_language(normalized)).lower()
    translated = False
    translation_error = None
    output_message = normalized

    if input_language == "ur":
        output_message, translated, translation_error = translate_to_english(normalized, source_lang="ur")

    metadata: Dict[str, Any] = {
        "input_language": input_language,
        "translated": translated,
    }
    if translation_error:
        metadata["translation_error"] = translation_error
    if output_message != normalized:
        metadata["normalized_message"] = output_message

    return output_message, metadata


async def _handle_chat_request(
    message: str,
    original_message: str,
    user_repo: UserRepository,
    chat_repo: ChatHistoryRepository,
    clerk_id: Optional[str],
    user_id: Optional[str],
    session_id: Optional[str],
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> ChatResponse:
    if not message or not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    agent = get_router_agent()
    result = agent.process_query(message.strip(), clerk_id=clerk_id)

    if not result.get("success", False):
        raise HTTPException(
            status_code=500,
            detail=f"Agent processing failed: {result.get('error', 'Unknown error')}",
        )

    resolved_user_id: Optional[str] = None
    if clerk_id:
        try:
            user = await user_repo.get_user_by_clerk_id(clerk_id)
            if user and getattr(user, "id", None):
                resolved_user_id = str(user.id)
        except Exception:
            resolved_user_id = None
    if not resolved_user_id and user_id:
        resolved_user_id = user_id

    metadata = {
        "user_id": resolved_user_id,
        "session_id": session_id,
        "clerk_id": clerk_id,
        "query_length": len(original_message),
        "agent_type": result.get("classification", "unknown"),
    }
    if extra_metadata:
        metadata.update({k: v for k, v in extra_metadata.items() if v is not None})

    response_text = result.get("response", "No response generated")
    if metadata.get("input_language") == "ur":
        translated_response, did_translate, translation_error = translate_to_urdu(response_text, source_lang="en")
        if did_translate:
            response_text = translated_response
        if translation_error:
            metadata["response_translation_error"] = translation_error

    try:
        if resolved_user_id and session_id:
            existing = await chat_repo.get_by_user_and_session(resolved_user_id, session_id)
            now = datetime.utcnow()
            user_msg = {"role": "user", "content": original_message.strip(), "timestamp": now.isoformat()}
            ai_msg = {
                "role": "assistant",
                "content": result.get("response", ""),
                "timestamp": now.isoformat(),
                "_payload": {
                    "classification": result.get("classification"),
                    "properties": result.get("properties"),
                    "builders": result.get("builders"),
                    "services": result.get("services"),
                    "metadata": extra_metadata or {},
                },
            }
            messages = ((existing or {}).get("messages") or []) + [user_msg, ai_msg]
            await chat_repo.upsert_messages(resolved_user_id, session_id, messages)
    except Exception:
        pass

    return ChatResponse(
        success=True,
        response=response_text,
        classification=result.get("classification", "unknown"),
        properties=result.get("properties"),
        builders=result.get("builders"),
        services=result.get("services"),
        error=None,
        metadata=metadata,
    )


# --- Request/Response Models ---

class ChatRequest(BaseModel):
    """Request model for chat messages."""
    message: str = Field(..., description="The user's message/query", min_length=1, max_length=1000)
    user_id: Optional[str] = Field(None, description="Optional internal DB user ID for session tracking")
    clerk_id: Optional[str] = Field(None, description="Optional Clerk user ID for resolving internal user id")
    session_id: Optional[str] = Field(None, description="Optional session ID for conversation context")
    language_hint: Optional[str] = Field(None, description="Optional language hint (ur or en)")


class ChatResponse(BaseModel):
    """Response model for chat messages."""
    success: bool = Field(..., description="Whether the request was successful")
    response: str = Field(..., description="The agent's response message")
    classification: str = Field(..., description="The classification of the query (listing_agent, general_chat, etc.)")
    error: Optional[str] = Field(None, description="Error message if any")
    properties: Optional[List[Dict[str, Any]]] = Field(None, description="Properties search results")
    builders: Optional[List[Dict[str, Any]]] = Field(None, description="Builder search results")
    services: Optional[List[Dict[str, Any]]] = Field(None, description="Builder service search results")
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
    user_repo: UserRepository = Depends(get_user_repository),
    chat_repo: ChatHistoryRepository = Depends(get_chat_history_repository),
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
        normalized_message, language_metadata = _normalize_user_message(
            request.message,
            request.language_hint,
        )
        return await _handle_chat_request(
            message=normalized_message,
            original_message=request.message,
            user_repo=user_repo,
            chat_repo=chat_repo,
            clerk_id=request.clerk_id,
            user_id=request.user_id,
            session_id=request.session_id,
            extra_metadata=language_metadata,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/message/audio", response_model=ChatResponse)
async def send_audio_message(
    audio: UploadFile = File(..., description="WAV/FLAC audio file"),
    user_id: Optional[str] = Form(None),
    clerk_id: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    language_hint: Optional[str] = Form(None),
    user_repo: UserRepository = Depends(get_user_repository),
    chat_repo: ChatHistoryRepository = Depends(get_chat_history_repository),
):
    """
    Transcribe an audio clip and route it through the chat agent.

    Accepts multipart/form-data with a single audio file.
    """
    try:
        audio_bytes = await audio.read()
        transcript, asr_metadata = transcribe_audio_bytes(audio_bytes)

        if not transcript:
            return ChatResponse(
                success=False,
                response="",
                classification="unknown",
                error="Unable to transcribe audio",
                metadata={"asr": asr_metadata},
            )

        normalized_message, language_metadata = _normalize_user_message(
            transcript,
            language_hint,
        )
        extra_metadata = {
            **language_metadata,
            "transcript": transcript,
            "asr": asr_metadata,
        }

        return await _handle_chat_request(
            message=normalized_message,
            original_message=transcript,
            user_repo=user_repo,
            chat_repo=chat_repo,
            clerk_id=clerk_id,
            user_id=user_id,
            session_id=session_id,
            extra_metadata=extra_metadata,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# =============================
# Unified WebSocket Chat Endpoint
# =============================

@router.websocket("/ws")
async def unified_chat_websocket(
    websocket: WebSocket,
    clerk_id: Optional[str] = None,
    session_id: Optional[str] = None
):
    """
    Unified WebSocket endpoint for all chat interactions.
    
    Handles:
    - General chat queries
    - Property/listing searches
    - Builder searches
    - Interactive profile creation
    - Interactive service creation
    
    Message format from client:
    {
        "type": "message",
        "text": "user message here",
        "clerk_id": "optional_clerk_id",
        "session_id": "optional_session_id"
    }
    
    Message format to client:
    {
        "type": "agent" | "completed" | "error" | "results",
        "message": "text response",
        "classification": "listing_agent" | "builder_agent" | "general_chat",
        "properties": [...],  # for listing results
        "builders": [...],     # for builder search results
        "services": [...],     # for service search results
        "success": true/false,
        "metadata": {...}
    }
    """
    await websocket.accept()
    print("=" * 80)
    print(f"WEBSOCKET CONNECTED - clerk_id: {clerk_id}, session_id: {session_id}")
    print("=" * 80)
    
    # State for interactive sessions
    active_creation_agent = None
    creation_type = None  # 'profile' or 'service'
    creation_state = None  # Persistent state for the creation agent
    
    try:
        while True:
            # Receive message from client
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected")
                break
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid message format. Please send JSON.",
                    "success": False
                })
                continue
            
            # Extract message details (user_id from frontend so we can persist when clerk lookup fails)
            message_text = data.get("text", "").strip()
            msg_clerk_id = data.get("clerk_id") or clerk_id
            msg_session_id = data.get("session_id") or session_id
            msg_user_id = (data.get("user_id") or "").strip() or None
            
            print("=" * 80)
            print(f"MESSAGE RECEIVED: '{message_text}'")
            print(f"clerk_id: {msg_clerk_id}, session_id: {msg_session_id}")
            print("=" * 80)
            
            logger.info(f"[WebSocket] Received message: '{message_text}' from clerk_id: {msg_clerk_id}")
            
            if not message_text:
                await websocket.send_json({
                    "type": "error",
                    "message": "Empty message received.",
                    "success": False
                })
                continue
            
            # Check if this is a property creation request
            message_type = data.get("type", "message")
            if message_type == "property_create":
                try:
                    if not msg_clerk_id:
                        await websocket.send_json({
                            "type": "error",
                            "message": "clerk_id is required for property listing creation.",
                            "success": False
                        })
                        continue
                    
                    # Import the property creation agent
                    from agents.listing.create_listing_agent import PropertyListingCreationAgent
                    property_agent = PropertyListingCreationAgent()
                    
                    # Define send/receive functions for the interactive agent
                    async def send(payload: Dict[str, Any]):
                        logger.info(f"[WebSocket] Property creation - Sending to client: {payload}")
                        await websocket.send_json(payload)
                    
                    async def recv_text() -> str:
                        try:
                            data = await websocket.receive_json()
                            logger.info(f"[WebSocket] Property creation - Received from client: {data}")
                            if isinstance(data, dict) and data.get("type") == "message":
                                return str(data.get("text", "")).strip()
                            if isinstance(data, dict) and "text" in data:
                                return str(data.get("text", "")).strip()
                            if isinstance(data, str):
                                return data
                            return ""
                        except WebSocketDisconnect:
                            logger.info("[WebSocket] Client disconnected during property creation")
                            return "cancel"
                        except Exception as e:
                            logger.error(f"Error receiving text: {e}")
                            return ""
                    
                    # Run the interactive agent
                    await property_agent.process_query_interactive(
                        query=message_text,
                        clerk_id=msg_clerk_id,
                        send=send,
                        recv_text=recv_text
                    )
                    logger.info("[WebSocket] Property creation session completed")
                    continue
                except Exception as e:
                    logger.error(f"Error in property creation: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "message": f"An error occurred during property creation: {str(e)}",
                        "success": False
                    })
                    continue
            
            # Check if this is a builder profile creation request
            if message_type == "builder_profile_create":
                try:
                    if not msg_clerk_id:
                        await websocket.send_json({
                            "type": "error",
                            "message": "clerk_id is required for builder profile creation.",
                            "success": False
                        })
                        continue
                    
                    # Import the profile creation agent
                    from agents.builder.create_profile_agent import BuilderProfileCreationAgent
                    profile_agent = BuilderProfileCreationAgent()
                    
                    # Define send/receive functions for the interactive agent
                    async def send_profile(payload: Dict[str, Any]):
                        logger.info(f"[WebSocket] Profile creation - Sending to client: {payload}")
                        await websocket.send_json(payload)
                    
                    async def recv_text_profile() -> str:
                        try:
                            data = await websocket.receive_json()
                            logger.info(f"[WebSocket] Profile creation - Received from client: {data}")
                            if isinstance(data, dict) and data.get("type") == "message":
                                return str(data.get("text", "")).strip()
                            if isinstance(data, dict) and "text" in data:
                                return str(data.get("text", "")).strip()
                            if isinstance(data, str):
                                return data
                            return ""
                        except WebSocketDisconnect:
                            logger.info("[WebSocket] Client disconnected during profile creation")
                            return "cancel"
                        except Exception as e:
                            logger.error(f"Error receiving text: {e}")
                            return ""
                    
                    # Run the interactive agent
                    await profile_agent.process_query_interactive(
                        query=message_text,
                        clerk_id=msg_clerk_id,
                        send=send_profile,
                        recv_text=recv_text_profile
                    )
                    logger.info("[WebSocket] Profile creation session completed")
                    continue
                except Exception as e:
                    logger.error(f"Error in profile creation: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "message": f"An error occurred during profile creation: {str(e)}",
                        "success": False
                    })
                    continue
            
            # Check if this is a builder service creation request
            if message_type == "builder_service_create":
                try:
                    if not msg_clerk_id:
                        await websocket.send_json({
                            "type": "error",
                            "message": "clerk_id is required for builder service creation.",
                            "success": False
                        })
                        continue
                    
                    # Import the service creation agent
                    from agents.builder.create_service_agent import BuilderServiceCreationAgent
                    service_agent = BuilderServiceCreationAgent()
                    
                    # Define send/receive functions for the interactive agent
                    async def send_service(payload: Dict[str, Any]):
                        logger.info(f"[WebSocket] Service creation - Sending to client: {payload}")
                        await websocket.send_json(payload)
                    
                    async def recv_text_service() -> str:
                        try:
                            data = await websocket.receive_json()
                            logger.info(f"[WebSocket] Service creation - Received from client: {data}")
                            if isinstance(data, dict) and data.get("type") == "message":
                                return str(data.get("text", "")).strip()
                            if isinstance(data, dict) and "text" in data:
                                return str(data.get("text", "")).strip()
                            if isinstance(data, str):
                                return data
                            return ""
                        except WebSocketDisconnect:
                            logger.info("[WebSocket] Client disconnected during service creation")
                            return "cancel"
                        except Exception as e:
                            logger.error(f"Error receiving text: {e}")
                            return ""
                    
                    # Run the interactive agent
                    await service_agent.process_query_interactive(
                        query=message_text,
                        clerk_id=msg_clerk_id,
                        send=send_service,
                        recv_text=recv_text_service
                    )
                    logger.info("[WebSocket] Service creation session completed")
                    continue
                except Exception as e:
                    logger.error(f"Error in service creation: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "message": f"An error occurred during service creation: {str(e)}",
                        "success": False
                    })
                    continue
            
            # Check if this is a builder profile form extraction request (for form filling)
            if message_type == "builder_profile_form_extract":
                try:
                    if not msg_clerk_id:
                        await websocket.send_json({
                            "type": "error",
                            "message": "clerk_id is required for builder profile form extraction.",
                            "success": False
                        })
                        continue
                    
                    # Import the profile form extraction agent
                    from agents.builder.profile_form_extraction_agent import BuilderProfileFormExtractionAgent
                    profile_form_agent = BuilderProfileFormExtractionAgent()
                    
                    # Define send/receive functions for the interactive agent
                    async def send_profile_form(payload: Dict[str, Any]):
                        logger.info(f"[WebSocket] Profile form extraction - Sending to client: {payload}")
                        await websocket.send_json(payload)
                    
                    async def recv_text_profile_form() -> str:
                        try:
                            data = await websocket.receive_json()
                            logger.info(f"[WebSocket] Profile form extraction - Received from client: {data}")
                            if isinstance(data, dict) and data.get("type") == "message":
                                return str(data.get("text", "")).strip()
                            if isinstance(data, dict) and "text" in data:
                                return str(data.get("text", "")).strip()
                            if isinstance(data, str):
                                return data
                            return ""
                        except WebSocketDisconnect:
                            logger.info("[WebSocket] Client disconnected during profile form extraction")
                            return "cancel"
                        except Exception as e:
                            logger.error(f"Error receiving text: {e}")
                            return ""
                    
                    # Run the interactive agent
                    await profile_form_agent.process_query_interactive(
                        query=message_text,
                        clerk_id=msg_clerk_id,
                        send=send_profile_form,
                        recv_text=recv_text_profile_form
                    )
                    logger.info("[WebSocket] Profile form extraction session completed")
                    continue
                except Exception as e:
                    logger.error(f"Error in profile form extraction: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "message": f"An error occurred during profile form extraction: {str(e)}",
                        "success": False
                    })
                    continue
            
            # Check if this is a builder service form extraction request (for form filling)
            if message_type == "builder_service_form_extract":
                try:
                    if not msg_clerk_id:
                        await websocket.send_json({
                            "type": "error",
                            "message": "clerk_id is required for builder service form extraction.",
                            "success": False
                        })
                        continue
                    
                    # Import the service form extraction agent
                    from agents.builder.service_form_extraction_agent import BuilderServiceFormExtractionAgent
                    service_form_agent = BuilderServiceFormExtractionAgent()
                    
                    # Define send/receive functions for the interactive agent
                    async def send_service_form(payload: Dict[str, Any]):
                        logger.info(f"[WebSocket] Service form extraction - Sending to client: {payload}")
                        await websocket.send_json(payload)
                    
                    async def recv_text_service_form() -> str:
                        try:
                            data = await websocket.receive_json()
                            logger.info(f"[WebSocket] Service form extraction - Received from client: {data}")
                            if isinstance(data, dict) and data.get("type") == "message":
                                return str(data.get("text", "")).strip()
                            if isinstance(data, dict) and "text" in data:
                                return str(data.get("text", "")).strip()
                            if isinstance(data, str):
                                return data
                            return ""
                        except WebSocketDisconnect:
                            logger.info("[WebSocket] Client disconnected during service form extraction")
                            return "cancel"
                        except Exception as e:
                            logger.error(f"Error receiving text: {e}")
                            return ""
                    
                    # Run the interactive agent
                    await service_form_agent.process_query_interactive(
                        query=message_text,
                        clerk_id=msg_clerk_id,
                        send=send_service_form,
                        recv_text=recv_text_service_form
                    )
                    logger.info("[WebSocket] Service form extraction session completed")
                    continue
                except Exception as e:
                    logger.error(f"Error in service form extraction: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "message": f"An error occurred during service form extraction: {str(e)}",
                        "success": False
                    })
                    continue
            
            # If we're in an active creation session, route to that agent
            if active_creation_agent is not None:
                try:
                    # The agent is already instantiated and running interactively
                    # Just send the message through the interactive handler
                    # This path should not be reached because we use process_query_interactive
                    # which handles the full conversation loop internally
                    logger.warning("Unexpected active_creation_agent state - should be using interactive method")
                    active_creation_agent = None
                    creation_type = None
                    creation_state = None
                except Exception as e:
                    logger.error(f"Error in creation agent: {e}", exc_info=True)
                    active_creation_agent = None
                    creation_type = None
                    creation_state = None
                    await websocket.send_json({
                        "type": "error",
                        "message": f"An error occurred: {str(e)}",
                        "success": False
                    })
                continue
            
            # Not in creation mode - route through main router agent
            print("=" * 80)
            print("ENTERING ROUTER PROCESSING BLOCK")
            print("=" * 80)
            try:
                print("INSIDE TRY BLOCK")
                logger.info("[WebSocket] About to call router_agent.process_query")
                router_agent = get_router_agent()
                print(f"CALLING router_agent.process_query with: {message_text}")
                result = router_agent.process_query(message_text, clerk_id=msg_clerk_id)
                print(f"RESULT RECEIVED: {result.keys() if isinstance(result, dict) else type(result)}")
                print(f"CLASSIFICATION: {result.get('classification')}")
                print(f"HAS METADATA: {bool(result.get('metadata'))}")
                print(f"METADATA VALUE: {result.get('metadata')}")
                logger.info(f"[WebSocket] Router returned, result type: {type(result)}, keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
                
                classification = result.get("classification", "unknown")
                print(f"EXTRACTED CLASSIFICATION: {classification}")
                
                logger.info(f"[WebSocket] Router result: classification={classification}, has_metadata={bool(result.get('metadata'))}, metadata={result.get('metadata')}")
                
                # Check if this is a creation task that needs interactive mode
                print(f"CHECKING: classification == 'builder_agent' ? {classification == 'builder_agent'}")
                if classification == "builder_agent":
                    print("INSIDE BUILDER_AGENT BLOCK")
                    logger.info(f"[WebSocket] Detected builder_agent classification")
                    # Check if the result indicates we should start an interactive session
                    metadata = result.get("metadata", {})
                    print(f"METADATA EXTRACTED: {metadata}")
                    logger.info(f"[WebSocket] Metadata extracted: {metadata}")
                    logger.info(f"[WebSocket] Has interactive_mode: {metadata.get('interactive_mode') if metadata else 'metadata is None/empty'}")
                    
                    print(f"CHECKING: metadata and metadata.get('interactive_mode') ? {metadata and metadata.get('interactive_mode')}")
                    if metadata and metadata.get("interactive_mode"):
                        print("STARTING INTERACTIVE SESSION!")
                        # Start interactive session with the specialized agent
                        agent_type = metadata.get("agent_type")  # 'profile' or 'service'
                        
                        logger.info(f"[WebSocket] Starting interactive {agent_type} creation session")
                        
                        if not msg_clerk_id:
                            await websocket.send_json({
                                "type": "error",
                                "message": f"clerk_id is required for {agent_type} creation.",
                                "success": False
                            })
                            continue
                        
                        # FIRST: Send the initial response message from the router to the frontend
                        # This lets the user know we're starting the interactive flow
                        initial_response = result.get("response", "")
                        if initial_response:
                            await websocket.send_json({
                                "type": "agent",
                                "message": initial_response,
                                "classification": classification,
                                "success": True,
                                "interactive_mode": True,
                                "metadata": metadata
                            })
                            logger.info(f"[WebSocket] Sent initial response to frontend: {initial_response[:100]}...")
                        
                        # Get the specialized agent from BuilderAgent
                        from agents.builder.agent import BuilderAgent
                        builder_agent = BuilderAgent()
                        
                        try:
                            specialized_agent = builder_agent.get_interactive_agent(agent_type)
                            logger.info(f"[WebSocket] Got specialized agent: {type(specialized_agent).__name__}")
                            
                            # Define send/receive functions for the interactive agent
                            async def send(payload: Dict[str, Any]):
                                logger.info(f"[WebSocket] Sending to client: {payload}")
                                await websocket.send_json(payload)
                            
                            async def recv_text() -> str:
                                try:
                                    data = await websocket.receive_json()
                                    logger.info(f"[WebSocket] Received from client: {data}")
                                    if isinstance(data, dict) and data.get("type") == "message":
                                        return str(data.get("text", "")).strip()
                                    if isinstance(data, dict) and "text" in data:
                                        return str(data.get("text", "")).strip()
                                    if isinstance(data, str):
                                        return data
                                    return ""
                                except WebSocketDisconnect:
                                    logger.info("[WebSocket] Client disconnected during interactive session")
                                    return "cancel"
                                except Exception as e:
                                    logger.error(f"Error receiving text: {e}")
                                    return ""
                            
                            # Run the interactive agent (it handles the full conversation loop)
                            # Pass the original message as the initial query
                            logger.info(f"[WebSocket] Calling process_query_interactive with query: {message_text}")
                            await specialized_agent.process_query_interactive(
                                query=message_text,
                                clerk_id=msg_clerk_id,
                                send=send,
                                recv_text=recv_text
                            )
                            logger.info(f"[WebSocket] Interactive session completed")
                            
                        except Exception as e:
                            logger.error(f"Error in interactive {agent_type} creation: {e}", exc_info=True)
                            await websocket.send_json({
                                "type": "error",
                                "message": f"An error occurred during {agent_type} creation: {str(e)}",
                                "success": False
                            })
                        
                        continue
                
                # Regular response (search, general chat, etc.)
                response_payload = {
                    "type": "agent",
                    "message": result.get("response", ""),
                    "classification": classification,
                    "success": result.get("success", True),
                }
                
                # Add results if present
                if result.get("properties"):
                    response_payload["properties"] = result["properties"]
                if result.get("builders"):
                    response_payload["builders"] = result["builders"]
                if result.get("services"):
                    response_payload["services"] = result["services"]
                if result.get("metadata"):
                    response_payload["metadata"] = result["metadata"]
                if result.get("error"):
                    response_payload["error"] = result["error"]
                
                # Persist chat history (Postgres) for websocket messages
                try:
                    if msg_session_id:
                        resolved_uid: Optional[str] = None
                        if msg_clerk_id:
                            async with get_db_session_ctx() as session:
                                user_repo_ws = UserRepository(session)
                                user_doc = await user_repo_ws.get_user_by_clerk_id(msg_clerk_id)
                                if user_doc is not None:
                                    resolved_uid = getattr(user_doc, "id", None) or getattr(user_doc, "_id", None)
                                    if resolved_uid is not None:
                                        resolved_uid = str(resolved_uid)
                        if not resolved_uid and msg_user_id:
                            resolved_uid = msg_user_id
                        if resolved_uid:
                            async with get_db_session_ctx() as session:
                                chat_repo_ws = ChatHistoryRepository(session)
                                now = datetime.utcnow()
                                user_msg = {"role": "user", "content": message_text, "timestamp": now.isoformat()}
                                ai_msg = {
                                    "role": "assistant",
                                    "content": result.get("response", ""),
                                    "timestamp": now.isoformat(),
                                    "_payload": {
                                        "classification": result.get("classification"),
                                        "properties": result.get("properties"),
                                        "builders": result.get("builders"),
                                        "services": result.get("services"),
                                    },
                                }
                                existing = await chat_repo_ws.get_by_user_and_session(resolved_uid, msg_session_id)
                                messages = ((existing or {}).get("messages") or []) + [user_msg, ai_msg]
                                await chat_repo_ws.upsert_messages(resolved_uid, msg_session_id, messages)
                                logger.info(f"[WebSocket] Persisted chat for user_id={resolved_uid} session_id={msg_session_id}")
                        else:
                            logger.warning("[WebSocket] Skip persist: no user_id (clerk_id lookup failed and no user_id in message)")
                except Exception as e:
                    logger.warning(f"[WebSocket] Failed to persist chat history: {e}", exc_info=True)

                await websocket.send_json(response_payload)
                
            except Exception as e:
                print("=" * 80)
                print(f"EXCEPTION CAUGHT: {type(e).__name__}: {e}")
                print("=" * 80)
                logger.error(f"Error processing message: {e}", exc_info=True)
                await websocket.send_json({
                    "type": "error",
                    "message": f"An error occurred while processing your message: {str(e)}",
                    "success": False
                })
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Connection error occurred.",
                "success": False
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass


# =============================
# Legacy WebSocket Endpoints (kept for backward compatibility)
# =============================

# @router.websocket("/ws/service/create")
# async def ws_service_create(websocket: WebSocket, clerk_id: str):
#     """Interactive websocket endpoint for the service creation agent.
#     Frontend connects and exchanges JSON messages: { type: 'user', text: '...' }
#     Server sends: { type: 'agent'|'completed'|'error', ... }
#     """
#     await websocket.accept()
#     if not clerk_id:
#         await websocket.send_json({"type": "error", "message": "Missing clerk_id. Cannot start service creation."})
#         await websocket.close()
#         return
#     agent = BuilderServiceCreationAgent()

#     async def send(payload: Dict[str, Any]):
#         await websocket.send_json(payload)

#     async def recv_text() -> str:
#         try:
#             data = await websocket.receive_json()
#             if isinstance(data, dict) and data.get("type") == "user":
#                 return str(data.get("text") or "").strip()
#             # Fallback to raw text
#             if isinstance(data, str):
#                 return data
#             return ""
#         except WebSocketDisconnect:
#             return "cancel"

#     # Expect the first client message to include the initial intent/query
#     first = await recv_text()
#     if not first:
#         await send({"type": "error", "message": "No initial message provided."})
#         await websocket.close()
#         return

#     try:
#         result = await agent.process_query_interactive(first, clerk_id=clerk_id, send=send, recv_text=recv_text)
#         # Ensure a final message is sent even if the agent exited early
#         try:
#             if isinstance(result, dict) and result.get("response"):
#                 await send({
#                     "type": "final",
#                     "text": result.get("response"),
#                     "success": result.get("success", False),
#                     "status": result.get("status", "unknown"),
#                 })
#         except Exception:
#             pass
#         await websocket.close()
#         return
#     except Exception as e:
#         await send({"type": "error", "message": str(e)})
#         await websocket.close()


# @router.websocket("/ws/profile/create")
# async def ws_profile_create(websocket: WebSocket, clerk_id: str):
#     """Interactive websocket endpoint for builder profile creation."""
#     await websocket.accept()
#     if not clerk_id:
#         await websocket.send_json({"type": "error", "message": "Missing clerk_id. Cannot start profile creation."})
#         await websocket.close()
#         return
#     agent = BuilderProfileCreationAgent()

# @router.post("/conversation", response_model=ChatResponse)
# async def start_conversation(request: ChatRequest, db: AsyncIOMotorDatabase = Depends(get_database)):
#     """
#     Start a new conversation with the chat agent.
    
#     This is an alias for the /message endpoint but with a more conversational name.
#     Useful for frontend applications that want to distinguish between single messages
#     and conversation starters.
#     """
#     return await send_message(request, db)


def _normalize_messages(msgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for m in msgs:
        mm = dict(m)
        ts = mm.get("timestamp")
        if isinstance(ts, datetime):
            mm["timestamp"] = ts.isoformat()
        elif isinstance(ts, str) and "T" in ts:
            pass
        out.append(mm)
    return out


def _get_ts(m: Dict[str, Any]) -> float:
    ts = m.get("timestamp")
    if isinstance(ts, datetime):
        return ts.timestamp()
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


@router.get("/history")
async def get_chat_history(
    user_id: str = Query(..., description="User ID (UUID)"),
    session_id: Optional[str] = Query(None, description="Filter messages by session id (optional)"),
    limit: int = Query(50, ge=1, le=200, description="Max messages to return (newest last)"),
    chat_repo: ChatHistoryRepository = Depends(get_chat_history_repository),
):
    """Return a user's chat history. user_id must be a valid UUID (404 if invalid)."""
    uid = parse_uuid(user_id, "user_id")
    if session_id:
        doc = await chat_repo.get_by_user_and_session(uid, session_id)
        if not doc:
            return {"count": 0, "messages": []}
        messages = list(doc.get("messages", []))
        updated_at = doc.get("updated_at")
        doc_id = doc.get("id")
    else:
        docs = await chat_repo.list_by_user_id(uid)
        if not docs:
            return {"count": 0, "messages": []}
        messages = []
        for d in docs:
            messages.extend(d.get("messages", []))
        latest = await chat_repo.get_latest_by_user_id(uid)
        updated_at = latest.get("updated_at") if latest else None
        doc_id = latest.get("id") if latest else None
    messages.sort(key=_get_ts)
    if len(messages) > limit:
        messages = messages[-limit:]
    return {
        "count": len(messages),
        "messages": _normalize_messages(messages),
        "updated_at": (updated_at.isoformat() if isinstance(updated_at, datetime) else str(updated_at) if updated_at else ""),
        "_id": doc_id,
    }


@router.get("/sessions")
async def list_chat_sessions(
    user_id: str = Query(..., description="User ID (UUID)"),
    chat_repo: ChatHistoryRepository = Depends(get_chat_history_repository),
):
    """Return a condensed list of prior sessions for the user. user_id must be a valid UUID (404 if invalid)."""
    uid = parse_uuid(user_id, "user_id")
    docs = await chat_repo.list_by_user_id(uid)
    if not docs:
        return {"count": 0, "sessions": []}

    # Aggregate sessions from all documents
    sessions: Dict[str, Dict[str, Any]] = {}
    for doc in docs:
        session_id_from_doc = doc.get("session_id")
        messages = doc.get("messages", [])
        updated_at = doc.get("updated_at")
        
        # Use session_id from document if available, otherwise extract from messages
        if session_id_from_doc:
            sid = session_id_from_doc
        elif messages:
            # Fallback: try to get session_id from first message payload
            first_msg = messages[0] if messages else {}
            payload = first_msg.get("_payload") or {}
            sid = payload.get("session_id") or "default"
        else:
            continue  # Skip documents without messages or session_id
        
        # Get the last message for preview
        last_message = ""
        last_timestamp = updated_at
        if messages:
            # Find the most recent message
            sorted_messages = sorted(
                messages,
                key=lambda m: m.get("timestamp", datetime.min) if isinstance(m.get("timestamp"), datetime) else datetime.min,
                reverse=True
            )
            if sorted_messages:
                last_msg = sorted_messages[0]
                last_message = last_msg.get("content", "")[:120]
                last_timestamp = last_msg.get("timestamp", updated_at)
        
        # Update session info if this is newer or if it doesn't exist
        if sid not in sessions:
            sessions[sid] = {
                "session_id": sid,
                "last_message": last_message,
                "updated_at": last_timestamp.isoformat() if isinstance(last_timestamp, datetime) else str(last_timestamp),
            }
        else:
            # Keep the most recent update
            existing_ts = sessions[sid].get("updated_at", "")
            new_ts = last_timestamp.isoformat() if isinstance(last_timestamp, datetime) else str(last_timestamp)
            if new_ts > existing_ts:
                sessions[sid]["last_message"] = last_message
                sessions[sid]["updated_at"] = new_ts

    # sort by updated_at desc
    def _ts_iso(v: str) -> float:
        try:
            if isinstance(v, datetime):
                return v.timestamp()
            return datetime.fromisoformat(v).timestamp()
        except Exception:
            return 0.0

    sorted_sessions = sorted(
        sessions.values(),
        key=lambda s: _ts_iso(s.get("updated_at", "")),
        reverse=True,
    )

    return {"count": len(sorted_sessions), "sessions": sorted_sessions}


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    session_id: str,
    user_id: str = Query(..., description="User ID (UUID)"),
    chat_repo: ChatHistoryRepository = Depends(get_chat_history_repository),
):
    """Delete a chat session for the given user/session_id. user_id must be a valid UUID (404 if invalid)."""
    uid = parse_uuid(user_id, "user_id")
    await chat_repo.delete_by_user_and_session(uid, session_id)
    return None
# # --- Additional Utility Endpoints ---

# @router.get("/capabilities")
# async def get_capabilities():
#     """
#     Get information about what the chat agent can do.
#     """
#     return {
#         "capabilities": [
#             "Property search and real estate queries",
#             "General conversation and platform help",
#             "Intelligent query classification and routing",
#             "Multi-agent orchestration"
#         ],
#         "supported_queries": [
#             "Property searches (e.g., 'Find houses in Islamabad')",
#             "General questions (e.g., 'What is PropPal?')",
#             "Platform help (e.g., 'How do I create an account?')",
#             "Mixed queries (e.g., 'Hi, I need help with property search')"
#         ],
#         "agents": {
#             "listing_agent": "Handles property searches and real estate queries",
#             "general_chat": "Handles general conversation and platform help"
#         }
#     }


# @router.get("/status")
# async def get_status():
#     """
#     Get detailed status information about the chat service.
#     """
#     try:
#         # Test the agent with a simple query
#         agent = get_router_agent()
#         test_result = agent.process_query("Hello")
        
#         return {
#             "status": "operational" if test_result.get("success") else "degraded",
#             "agent_name": agent.name,
#             "last_test": {
#                 "query": "Hello",
#                 "success": test_result.get("success"),
#                 "classification": test_result.get("classification"),
#                 "response_length": len(test_result.get("response", ""))
#             },
#             "timestamp": "2024-01-01T00:00:00Z"  # You might want to use actual timestamp
#         }
#     except Exception as e:
#         return {
#             "status": "error",
#             "error": str(e),
#             "agent_name": "RouterAgent"
#         }


# # =============================
# # Read endpoints for chat logs
# # =============================

# def _str_oid(value: Any) -> Any:
#     try:
#         if isinstance(value, ObjectId):
#             return str(value)
#     except Exception:
#         pass
#     return value

# def _normalize_messages(msgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#     out: List[Dict[str, Any]] = []
#     for m in msgs:
#         mm = {k: _str_oid(v) for k, v in m.items()}
#         # ensure timestamp is ISO string
#         ts = mm.get("timestamp")
#         if isinstance(ts, datetime):
#             mm["timestamp"] = ts.isoformat()
#         out.append(mm)
#     return out


# @router.get("/history")
# async def get_chat_history(
#     user_id: str = Query(..., description="User id (Mongo ObjectId, external, or 'session:<sid>')"),
#     session_id: Optional[str] = Query(None, description="Filter messages by session id (optional)"),
#     limit: int = Query(50, ge=1, le=200, description="Max messages to return (newest last)"),
#     db: AsyncIOMotorDatabase = Depends(get_database),
# ):
#     """Return a user's chat history. If session_id is provided, messages are filtered to that session.
#     Messages are returned ascending by time and capped by limit (last N).
#     """
#     query_id: Any = user_id
#     if user_id.startswith("session:"):
#         query_id = user_id
#     elif ObjectId.is_valid(user_id):
#         query_id = ObjectId(user_id)

#     doc = await db["chat_histories"].find_one({"user_id": query_id})
#     if not doc:
#         return {"count": 0, "messages": []}

#     messages: List[Dict[str, Any]] = doc.get("messages", [])
#     if session_id:
#         messages = [m for m in messages if m.get("_payload", {}).get("session_id") == session_id]

#     # sort by timestamp ascending
#     def _get_ts(m: Dict[str, Any]) -> float:
#         ts = m.get("timestamp")
#         if isinstance(ts, datetime):
#             return ts.timestamp()
#         try:
#             return datetime.fromisoformat(ts).timestamp()
#         except Exception:
#             return 0.0

#     messages.sort(key=_get_ts)
#     if len(messages) > limit:
#         messages = messages[-limit:]

#     return {
#         "count": len(messages),
#         "messages": _normalize_messages(messages),
#         "updated_at": (doc.get("updated_at").isoformat() if isinstance(doc.get("updated_at"), datetime) else doc.get("updated_at")),
#         "_id": _str_oid(doc.get("_id")),
#     }


# @router.get("/history/messages")
# async def get_chat_messages_paginated(
#     user_id: str = Query(..., description="User id (Mongo ObjectId, external, or 'session:<sid>')"),
#     session_id: Optional[str] = Query(None),
#     before_ms: Optional[int] = Query(None, description="Return messages older than this epoch ms"),
#     limit: int = Query(50, ge=1, le=200),
#     db: AsyncIOMotorDatabase = Depends(get_database),
# ):
#     """Cursor-style pagination for messages (newest to oldest).
#     Pass before_ms to page older messages. Returns nextBeforeMs if more exist.
#     """
#     query_id: Any = user_id
#     if user_id.startswith("session:"):
#         query_id = user_id
#     elif ObjectId.is_valid(user_id):
#         query_id = ObjectId(user_id)

#     doc = await db["chat_histories"].find_one({"user_id": query_id})
#     if not doc:
#         return {"count": 0, "messages": [], "nextBeforeMs": None}

#     messages: List[Dict[str, Any]] = doc.get("messages", [])
#     if session_id:
#         messages = [m for m in messages if m.get("_payload", {}).get("session_id") == session_id]

#     # to newest-first order
#     def _ts(m: Dict[str, Any]) -> float:
#         t = m.get("timestamp")
#         if isinstance(t, datetime):
#             return t.timestamp()
#         try:
#             return datetime.fromisoformat(t).timestamp()
#         except Exception:
#             return 0.0

#     messages.sort(key=_ts, reverse=True)

#     if before_ms is not None:
#         messages = [m for m in messages if _ts(m) * 1000 < before_ms]

#     page = messages[:limit]
#     next_before = int(_ts(page[-1]) * 1000) if len(page) == limit else None

#     # Return ascending for rendering if preferred by client; keep newest-last here
#     page.reverse()
#     return {
#         "count": len(page),
#         "messages": _normalize_messages(page),
#         "nextBeforeMs": next_before,
#     }


# @router.get("/sessions")
# async def list_chat_sessions(
#     user_id: str = Query(..., description="User id (Mongo ObjectId, external, or 'session:<sid>')"),
#     db: AsyncIOMotorDatabase = Depends(get_database),
# ):
#     """Return a condensed list of prior sessions (by session_id) with last message and updated time.
#     This derives sessions from the _payload.session_id embedded in messages.
#     """
#     query_id: Any = user_id
#     if user_id.startswith("session:"):
#         query_id = user_id
#     elif ObjectId.is_valid(user_id):
#         query_id = ObjectId(user_id)

#     doc = await db["chat_histories"].find_one({"user_id": query_id})
#     if not doc:
#         return {"count": 0, "sessions": []}

#     sessions: Dict[str, Dict[str, Any]] = {}
#     for m in doc.get("messages", []):
#         payload = m.get("_payload") or {}
#         sid = payload.get("session_id") or "default"
#         ts = m.get("timestamp")
#         ts_val = ts.isoformat() if isinstance(ts, datetime) else ts
#         entry = sessions.get(sid) or {"session_id": sid, "last_message": "", "updated_at": ts_val}
#         # prefer assistant text or user text as preview
#         preview = m.get("content") or ""
#         entry["last_message"] = preview[:120]
#         entry["updated_at"] = ts_val
#         sessions[sid] = entry

#     # sort by updated_at desc
#     def _ts_iso(v: str) -> float:
#         try:
#             return datetime.fromisoformat(v).timestamp()
#         except Exception:
#             return 0.0

#     items = list(sessions.values())
#     items.sort(key=lambda x: _ts_iso(x.get("updated_at") or ""), reverse=True)
#     return {"count": len(items), "sessions": items}
