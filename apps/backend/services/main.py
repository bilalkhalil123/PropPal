"""
PropPal API Gateway Service

Main FastAPI application using the common utilities for:
- Configuration management (Pydantic Settings)
- Database connection (Motor async MongoDB)
- Error handling (Custom exceptions)
"""

import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

# Add parent directory to path to import common module
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.config import get_settings  # noqa: E402
from common.db import DatabaseClient, get_db_client  # noqa: E402
from common.errors import register_exception_handlers, DatabaseConnectionException  # noqa: E402
from api.users.router import router as users_router  # noqa: E402
from api.search.router import router as search_router  # noqa: E402
from api.chat.router import router as chat_router  # noqa: E402


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
        print(f"[STARTUP] [OK] MongoDB Atlas connection successful to database: {settings.MONGODB_DB_NAME}")

        # 2. Application RUNTIME
        yield

    except Exception as e:
        print(f"[STARTUP] [ERROR] Failed to connect to MongoDB: {e}")
        DatabaseClient.client = None
        DatabaseClient.database = None
        yield

    finally:
        # --- SHUTDOWN PHASE (AFTER YIELD) ---
        if DatabaseClient.client:
            # 3. Close DB Client
            DatabaseClient.client.close()
            print("[SHUTDOWN] [INFO] MongoDB client connection closed")


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

# Include API routers
app.include_router(users_router)
app.include_router(search_router)
app.include_router(chat_router)

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
