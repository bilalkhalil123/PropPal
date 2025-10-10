"""
PropPal API Gateway Service

Main FastAPI application using the common utilities for:
- Configuration management (Pydantic Settings)
- Database connection (Motor async MongoDB)
- Error handling (Custom exceptions)
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

# Import common utilities
import sys
from pathlib import Path

# Add parent directory to path to import common module
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.config import Settings, get_settings
from common.db import DatabaseClient, get_db_client, get_database
from common.errors import (
    register_exception_handlers,
    ResourceNotFoundException,
    DatabaseConnectionException
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for FastAPI application.
    Manages startup and shutdown events for database connection.
    """
    # --- STARTUP PHASE (BEFORE YIELD) ---
    settings = get_settings()
    
    try:
        # 1. Initialize DB Client (Creation/Connection)
        print(f"[STARTUP] Connecting to MongoDB at {settings.MONGODB_URL[:20]}...")
        
        DatabaseClient.client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000  # Retry mechanism for Atlas latency
        )
        
        # Get database reference
        DatabaseClient.database = DatabaseClient.client[settings.MONGODB_DB_NAME]
        
        # Optional: Run a quick command to verify connection
        await DatabaseClient.client.admin.command('ping')
        print(f"[STARTUP] ✅ MongoDB Atlas connection successful to database: {settings.MONGODB_DB_NAME}")
        
        # 2. Application RUNTIME
        yield
        
    except Exception as e:
        print(f"[STARTUP] ❌ Failed to connect to MongoDB: {e}")
        DatabaseClient.client = None
        DatabaseClient.database = None
        yield
        
    finally:
        # --- SHUTDOWN PHASE (AFTER YIELD) ---
        if DatabaseClient.client:
            # 3. Close DB Client
            DatabaseClient.client.close()
            print("[SHUTDOWN] 📪 MongoDB client connection closed")


# Get settings
settings = get_settings()

# Initialize FastAPI app with lifespan
app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-Agent AI-Powered Real Estate Platform - Gateway Service",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    debug=settings.DEBUG
)

# Register custom exception handlers
register_exception_handlers(app)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================================
# Health Check Endpoints
# =====================================================================

@app.get("/")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health/database")
async def database_health_check(
    client: AsyncIOMotorClient = Depends(get_db_client)
):
    """
    Check MongoDB database connection status.
    
    Uses dependency injection to get the database client.
    """
    settings = get_settings()
    
    try:
        # Ping the database
        await client.admin.command('ping')
        
        # Get server info
        server_info = await client.server_info()
        
        # Get database and count collections
        db = client[settings.MONGODB_DB_NAME]
        collections = await db.list_collection_names()
        
        return {
            "status": "ok",
            "connected": True,
            "database": settings.MONGODB_DB_NAME,
            "mongodb_version": server_info.get("version", "unknown"),
            "collections_count": len(collections),
            "collections": collections,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise DatabaseConnectionException(
            message=f"Database health check failed: {str(e)}",
            details={"database": settings.MONGODB_DB_NAME}
        )


# =====================================================================
# Test Endpoints (for development/testing)
# =====================================================================

@app.post("/test/insert")
async def test_database_insert(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Test endpoint to insert a sample document.
    
    Uses dependency injection to get the database instance.
    """
    try:
        test_collection = db["test_collection"]
        
        # Insert a test document
        test_doc = {
            "message": "Test document from PropPal Gateway",
            "timestamp": datetime.utcnow(),
            "type": "test",
            "service": "gateway"
        }
        
        result = await test_collection.insert_one(test_doc)
        
        return {
            "status": "success",
            "message": "Test document inserted successfully",
            "inserted_id": str(result.inserted_id),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise DatabaseConnectionException(
            message=f"Insert operation failed: {str(e)}"
        )


@app.get("/test/documents")
async def test_get_documents(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Test endpoint to retrieve documents from test collection.
    
    Uses dependency injection to get the database instance.
    """
    try:
        test_collection = db["test_collection"]
        
        # Get all documents from test collection (limit 10)
        documents = await test_collection.find().limit(10).to_list(10)
        
        # Convert ObjectId to string for JSON serialization
        for doc in documents:
            doc["_id"] = str(doc["_id"])
            if "timestamp" in doc and hasattr(doc["timestamp"], "isoformat"):
                doc["timestamp"] = doc["timestamp"].isoformat()
        
        return {
            "status": "success",
            "count": len(documents),
            "documents": documents,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise DatabaseConnectionException(
            message=f"Query operation failed: {str(e)}"
        )


@app.get("/test/demo-error")
async def demo_custom_error():
    """
    Demo endpoint to test custom error handling.
    
    Raises a ResourceNotFoundException to demonstrate error handling.
    """
    raise ResourceNotFoundException(
        message="This is a demo error to test custom exception handling",
        details={
            "resource_type": "demo",
            "resource_id": "12345"
        }
    )


# =====================================================================
# Chat Endpoint (Placeholder for NLP Integration)
# =====================================================================

@app.post("/chat")
async def chat(query: Dict[str, str]):
    """
    Chat endpoint (placeholder for future NLP integration).
    
    Will eventually integrate with the NLP/RAG service.
    """
    settings = get_settings()
    
    return {
        "answer": f"You said: {query.get('query', 'nothing')}",
        "nlp_service": settings.NLP_SERVICE_URL,
        "timestamp": datetime.utcnow().isoformat(),
        "note": "This is a placeholder. NLP integration coming soon."
    }


# =====================================================================
# Application Entry Point
# =====================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
