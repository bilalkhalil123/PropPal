"""
Improved Chat API endpoint for AI agent communication.

This endpoint provides:
- Generic agent routing (extensible for multiple agents)
- Robust error handling
- Performance monitoring
- Structured request/response models
"""
import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.db import get_database
from agents.listing.agent import ListingAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ========== Request/Response Models ==========

class ChatRequest(BaseModel):
    """Enhanced request model for chat queries."""
    message: str = Field(..., description="User's natural language query", min_length=1, max_length=1000)
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context (preferences, history, etc.)")
    agent_type: Optional[str] = Field("listing", description="Type of agent to use (default: listing)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Find me a 3 bedroom house in Islamabad",
                "user_id": "user123",
                "session_id": "session456",
                "context": {
                    "preferences": {
                        "max_price": 5000000,
                        "min_bedrooms": 3
                    }
                },
                "agent_type": "listing"
            }
        }


class ChatResponse(BaseModel):
    """Enhanced response model for chat responses."""
    success: bool = Field(..., description="Whether the request was successful")
    response: str = Field(..., description="Natural language response")
    agent: str = Field(..., description="Name of the agent that processed the request")
    data: Optional[Dict[str, Any]] = Field(None, description="Agent-specific data")
    
    # Backward compatibility fields for ListingAgent
    properties: Optional[list] = Field(None, description="Properties found (for listing agent)")
    count: Optional[int] = Field(None, description="Number of items found")
    
    # Metadata
    intent: Optional[str] = Field(None, description="Detected intent")
    confidence: Optional[float] = Field(None, description="Intent confidence (0.0 to 1.0)")
    error: Optional[str] = Field(None, description="Error message if any")
    error_code: Optional[str] = Field(None, description="Error code for programmatic handling")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "response": "I found 10 properties matching your search.",
                "agent": "ListingAgent",
                "properties": [],
                "count": 10,
                "intent": "property_search",
                "confidence": 0.95,
                "error": None,
                "error_code": None,
                "processing_time": 1.23
            }
        }


# ========== Agent Management ==========

# Global agent registry (in production, use proper dependency injection)
_agent_registry: Dict[str, Any] = {}


def get_listing_agent(db: AsyncIOMotorDatabase = Depends(get_database)) -> ListingAgent:
    """Get or create Listing Agent instance with dependency injection."""
    global _agent_registry
    
    if "listing" not in _agent_registry:
        logger.info("🏠 Initializing ListingAgent...")
        _agent_registry["listing"] = ListingAgent(db=db)
        logger.info("✅ ListingAgent initialized")
    
    return _agent_registry["listing"]


def get_agent_by_type(agent_type: str, db: AsyncIOMotorDatabase) -> Optional[Any]:
    """
    Get agent by type - extensible for future agents.
    
    Args:
        agent_type: Type of agent (e.g., 'listing', 'booking', 'support')
        db: Database connection
        
    Returns:
        Agent instance or None if not found
    """
    if agent_type == "listing":
        return get_listing_agent(db)
    
    # Future agents can be added here:
    # elif agent_type == "booking":
    #     return get_booking_agent(db)
    # elif agent_type == "support":
    #     return get_support_agent(db)
    
    return None


# ========== API Endpoints ==========

@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Main chat endpoint for AI agent communication.
    
    Workflow:
    1. Receive user query
    2. Route to appropriate agent based on agent_type
    3. Agent analyzes intent using LLM
    4. Agent selects and executes appropriate tool
    5. Agent generates natural language response
    6. Return structured response to client
    
    The workflow is:
    - Generic and extensible for any agent type
    - Robust with comprehensive error handling
    - Efficient with performance monitoring
    - Well-logged for debugging and analytics
    """
    start_time = None
    
    try:
        import time
        start_time = time.time()
        
        logger.info(f"🤖 [CHAT] Received query from user: {request.user_id or 'anonymous'}")
        logger.info(f"📝 Query: {request.message}")
        logger.info(f"🎯 Agent type: {request.agent_type}")
        
        # Get the appropriate agent
        agent = get_agent_by_type(request.agent_type or "listing", db)
        
        if not agent:
            logger.error(f"❌ Unknown agent type: {request.agent_type}")
            raise HTTPException(
                status_code=400,
                detail=f"Unknown agent type: {request.agent_type}. Available types: listing"
            )
        
        # Process the query through the agent's LangGraph workflow
        # Note: process_query is synchronous, not async
        result = agent.process_query(
            query=request.message,
            user_id=request.user_id,
            session_id=request.session_id,
            context=request.context
        )
        
        processing_time = time.time() - start_time if start_time else 0
        
        logger.info(f"✅ [CHAT] Query processed successfully")
        logger.info(f"🤖 Agent: {result.get('agent', 'unknown')}")
        logger.info(f"🎯 Intent: {result.get('intent', 'unknown')}")
        logger.info(f"📊 Confidence: {result.get('confidence', 0):.2f}")
        logger.info(f"⏱️  Total time: {processing_time:.2f}s")
        
        # Return response
        return ChatResponse(
            success=result.get("success", False),
            response=result.get("response", "No response generated"),
            agent=result.get("agent", "Unknown"),
            data=result.get("data"),
            properties=result.get("properties"),
            count=result.get("count"),
            intent=result.get("intent"),
            confidence=result.get("confidence"),
            error=result.get("error"),
            error_code=result.get("error_code"),
            processing_time=result.get("processing_time", processing_time)
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        import time
        processing_time = time.time() - start_time if start_time else 0
        
        logger.error(f"❌ [CHAT] Fatal error: {str(e)}")
        logger.error(f"⏱️  Failed after: {processing_time:.2f}s")
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )


@router.get("/agents")
async def list_agents(db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    List all available AI agents and their capabilities.
    
    This endpoint is generic and automatically discovers agents
    from the agent registry.
    """
    agents = []
    
    # Get listing agent info
    listing_agent = get_listing_agent(db)
    if listing_agent:
        agent_info = listing_agent.get_agent_info()
        agents.append({
            "type": "listing",
            "name": agent_info["name"],
            "description": agent_info["description"],
            "capabilities": ["property_search", "property_discovery", "area_search"],
            "tools": agent_info["tools"],
            "stats": agent_info["stats"],
            "status": "active"
        })
    
    # Future agents will be added here automatically
    # booking_agent = get_booking_agent(db)
    # if booking_agent:
    #     agents.append(booking_agent.get_agent_info())
    
    return {
        "agents": agents,
        "total": len(agents)
    }


@router.get("/agents/{agent_type}")
async def get_agent_info(
    agent_type: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get detailed information about a specific agent."""
    agent = get_agent_by_type(agent_type, db)
    
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent type '{agent_type}' not found"
        )
    
    return agent.get_agent_info()


@router.get("/health")
async def chat_health(db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Health check for chat service.
    
    Checks:
    - Service availability
    - Agent initialization
    - LLM connectivity (Ollama)
    - Database connectivity
    """
    health_status = {
        "status": "healthy",
        "agents_available": False,
        "ollama_connected": False,
        "database_connected": False,
        "errors": []
    }
    
    try:
        # Check agent availability
        listing_agent = get_listing_agent(db)
        if listing_agent:
            health_status["agents_available"] = True
        
        # Check Ollama connectivity (basic check)
        try:
            # This will fail fast if Ollama is not available
            test_response = listing_agent.llm.invoke("test")
            health_status["ollama_connected"] = True
        except Exception as e:
            health_status["errors"].append(f"Ollama error: {str(e)}")
            health_status["ollama_connected"] = False
        
        # Check database connectivity
        try:
            await db.command("ping")
            health_status["database_connected"] = True
        except Exception as e:
            health_status["errors"].append(f"Database error: {str(e)}")
            health_status["database_connected"] = False
        
        # Overall health status
        if health_status["agents_available"] and health_status["ollama_connected"]:
            health_status["status"] = "healthy"
        elif health_status["agents_available"]:
            health_status["status"] = "degraded"
        else:
            health_status["status"] = "unhealthy"
        
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["errors"].append(f"Health check error: {str(e)}")
    
    return health_status


@router.post("/agents/{agent_type}/reset-stats")
async def reset_agent_stats(
    agent_type: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Reset performance statistics for a specific agent."""
    agent = get_agent_by_type(agent_type, db)
    
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent type '{agent_type}' not found"
        )
    
    agent.reset_stats()
    
    return {
        "message": f"Statistics reset for {agent.name}",
        "agent": agent.name
    }
