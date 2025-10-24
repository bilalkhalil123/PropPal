"""
Chat API with RouterAgent integration.
Provides conversational interface using the RouterAgent orchestrator.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents import RouterAgent

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
    user_id: Optional[str] = Field(None, description="Optional user ID for session tracking")
    session_id: Optional[str] = Field(None, description="Optional session ID for conversation context")


class ChatResponse(BaseModel):
    """Response model for chat messages."""
    success: bool = Field(..., description="Whether the request was successful")
    response: str = Field(..., description="The agent's response message")
    classification: str = Field(..., description="The classification of the query (listing_agent, general_chat, etc.)")
    error: Optional[str] = Field(None, description="Error message if any")
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
async def send_message(request: ChatRequest):
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
        
        # Prepare metadata
        metadata = {
            "user_id": request.user_id,
            "session_id": request.session_id,
            "query_length": len(request.message),
            "agent_type": result.get("classification", "unknown")
        }
        
        # Return the response
        return ChatResponse(
            success=True,
            response=result.get("response", "No response generated"),
            classification=result.get("classification", "unknown"),
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
async def start_conversation(request: ChatRequest):
    """
    Start a new conversation with the chat agent.
    
    This is an alias for the /message endpoint but with a more conversational name.
    Useful for frontend applications that want to distinguish between single messages
    and conversation starters.
    """
    return await send_message(request)


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
