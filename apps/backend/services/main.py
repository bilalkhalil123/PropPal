"""
PropPal API Gateway Service

Main FastAPI application using the common utilities for:
- Configuration management (Pydantic Settings)
- Database connection (PostgreSQL async via SQLAlchemy)
- Error handling (Custom exceptions)
"""

import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path to import common module
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.config import get_settings  # noqa: E402
from common.db import (  # noqa: E402
    get_async_session_factory,
    dispose_async_engine,
    get_db_session,
)
from common.errors import register_exception_handlers, DatabaseConnectionException  # noqa: E402
from api.users.router import router as users_router  # noqa: E402
from api.auth.router import router as auth_router  # noqa: E402
from api.search.router import router as search_router  # noqa: E402
from api.chat.router import router as chat_router  # noqa: E402
from api.builder.router import router as builder_router
from api.properties.router import router as properties_router
from api.recommendations.router import router as recommendations_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for FastAPI application.
    Manages startup and shutdown for PostgreSQL connection.
    """
    import asyncio
    settings = get_settings()
    # --- STARTUP: ensure Postgres engine/session factory exist for this event loop ---
    try:
        postgres_url = settings.get_postgres_url()
        if postgres_url:
            # Create engine and session factory for the main event loop
            get_async_session_factory(asyncio.get_running_loop())
            db_name = _db_name_from_url(postgres_url)
            print(f"[STARTUP] PostgreSQL engine ready (database: {db_name})")
        else:
            print("[STARTUP] [WARN] DATABASE_URL/POSTGRES_URL not set; DB features disabled")
    except Exception as e:
        print(f"[STARTUP] [ERROR] Failed to init PostgreSQL: {e}")

    yield

    # --- SHUTDOWN: dispose Postgres engine ---
    await dispose_async_engine()
    print("[SHUTDOWN] [INFO] PostgreSQL engine disposed")


def _db_name_from_url(url: str) -> str:
    """Extract database name from Postgres URL for display (no credentials)."""
    try:
        if "?" in url:
            path = url.split("?")[0]
        else:
            path = url
        parts = path.rstrip("/").split("/")
        if len(parts) >= 2:
            return parts[-1] or "postgres"
        return "postgres"
    except Exception:
        return "postgres"


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
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(search_router)
app.include_router(chat_router)
app.include_router(builder_router)
app.include_router(properties_router)
app.include_router(recommendations_router)

# Import and include storage router
from api.storage.router import router as storage_router
app.include_router(storage_router)

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
async def database_health_check(session=Depends(get_db_session)):
    """
    Check PostgreSQL database connection status.
    Runs SELECT 1 and returns DB name/version from the connection URL.
    """
    from sqlalchemy import text

    settings = get_settings()
    postgres_url = settings.get_postgres_url()
    if not postgres_url:
        raise DatabaseConnectionException(
            message="DATABASE_URL/POSTGRES_URL not configured",
            details={"database": "postgres"}
        )

    try:
        await session.execute(text("SELECT 1"))
        version_row = await session.execute(text("SELECT version()"))
        version = (version_row.scalar() or "unknown").strip()
        db_name = _db_name_from_url(postgres_url)

        return {
            "status": "ok",
            "connected": True,
            "database": db_name,
            "postgres_version": version,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise DatabaseConnectionException(
            message=f"Database health check failed: {str(e)}",
            details={"database": _db_name_from_url(postgres_url)}
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
