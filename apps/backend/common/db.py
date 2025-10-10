"""
MongoDB database connection management for PropPal backend services.

Uses Motor (async MongoDB driver) for FastAPI compatibility.
Implements singleton pattern for database client management.
"""

from typing import Optional

from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


class DatabaseClient:
    """
    Singleton-style database client manager.
    
    Stores the active MongoDB client instance and provides
    access to the database throughout the application lifecycle.
    """
    
    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        """
        Get the MongoDB client instance.
        
        Returns:
            AsyncIOMotorClient: The active MongoDB client
            
        Raises:
            HTTPException: If client is not initialized
        """
        if cls.client is None:
            raise HTTPException(
                status_code=500,
                detail="Database client not initialized. Ensure lifespan context is running."
            )
        return cls.client
    
    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """
        Get the MongoDB database instance.
        
        Returns:
            AsyncIOMotorDatabase: The active database instance
            
        Raises:
            HTTPException: If database is not initialized
        """
        if cls.database is None:
            raise HTTPException(
                status_code=500,
                detail="Database not initialized. Ensure lifespan context is running."
            )
        return cls.database


async def get_db_client() -> AsyncIOMotorClient:
    """
    FastAPI dependency to inject the MongoDB client.
    
    Usage:
        ```python
        @app.get("/items")
        async def get_items(client: AsyncIOMotorClient = Depends(get_db_client)):
            db = client[settings.MONGODB_DB_NAME]
            items = await db.items.find().to_list(100)
            return items
        ```
    
    Returns:
        AsyncIOMotorClient: The active MongoDB client
        
    Raises:
        HTTPException: If client is not initialized
    """
    return DatabaseClient.get_client()


async def get_database() -> AsyncIOMotorDatabase:
    """
    FastAPI dependency to inject the MongoDB database.
    
    Usage:
        ```python
        @app.get("/items")
        async def get_items(db: AsyncIOMotorDatabase = Depends(get_database)):
            items = await db.items.find().to_list(100)
            return items
        ```
    
    Returns:
        AsyncIOMotorDatabase: The active database instance
        
    Raises:
        HTTPException: If database is not initialized
    """
    return DatabaseClient.get_database()

