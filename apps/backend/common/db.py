"""
MongoDB database connection management for PropPal backend services.

Provides a singleton-style client plus a lazy `ensure_database_connection`
helper so that the API can recover gracefully if the FastAPI lifespan hook
didn't run (e.g. when the app is imported outside of uvicorn or during tests).
"""

import asyncio
from typing import Optional

from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import get_settings


class DatabaseClient:
    """Tracks the currently active MongoDB client/database instances."""

    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None


_db_init_lock = asyncio.Lock()


async def ensure_database_connection() -> AsyncIOMotorDatabase:
    """
    Lazily establish a MongoDB connection if the lifespan hook has not run.

    Returns:
        AsyncIOMotorDatabase: The connected database instance.
    """
    if DatabaseClient.database is not None and DatabaseClient.client is not None:
        return DatabaseClient.database

    async with _db_init_lock:
        if DatabaseClient.database is not None and DatabaseClient.client is not None:
            return DatabaseClient.database

        settings = get_settings()
        try:
            client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=5000,
            )
            await client.admin.command("ping")
            DatabaseClient.client = client
            DatabaseClient.database = client[settings.MONGODB_DB_NAME]
            return DatabaseClient.database
        except Exception as exc:
            if 'client' in locals():
                client.close()
            raise HTTPException(
                status_code  = 500,
                detail="Unable to connect to MongoDB. Ensure the database is reachable."
            ) from exc


async def get_db_client() -> AsyncIOMotorClient:
    """
    FastAPI dependency to inject the MongoDB client.

    Automatically initialises the client if the lifespan hook has not yet run.
    """
    if DatabaseClient.client is None:
        await ensure_database_connection()
    assert DatabaseClient.client is not None
    return DatabaseClient.client


async def get_database() -> AsyncIOMotorDatabase:
    """
    FastAPI dependency to inject the MongoDB database.

    Automatically initialises the database connection if required.
    """
    if DatabaseClient.database is None:
        await ensure_database_connection()
    assert DatabaseClient.database is not None
    return DatabaseClient.database

