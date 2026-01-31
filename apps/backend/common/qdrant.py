"""
Qdrant vector database client for storing and retrieving embeddings.

This module provides a singleton Qdrant client that connects to Qdrant
for vector similarity search operations.
"""

from functools import lru_cache
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from common.config import get_settings


class QdrantClientSingleton:
    """Singleton wrapper for Qdrant client."""
    
    _client: Optional[QdrantClient] = None
    
    @classmethod
    def get_client(cls) -> QdrantClient:
        """Get or create Qdrant client instance."""
        if cls._client is None:
            settings = get_settings()
            # Only use API key if provided and URL is HTTPS (cloud)
            api_key = None
            if hasattr(settings, 'QDRANT_API_KEY') and settings.QDRANT_API_KEY:
                if settings.QDRANT_URL.startswith('https://'):
                    api_key = settings.QDRANT_API_KEY
                elif settings.QDRANT_URL.startswith('http://'):
                    # Warn only if API key is set with HTTP (insecure)
                    import warnings
                    warnings.warn(
                        "QDRANT_API_KEY is set but QDRANT_URL uses HTTP (insecure). "
                        "For cloud instances, use HTTPS URL.",
                        UserWarning
                    )
            cls._client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=api_key,
                timeout=120,  # 2 min for batch upserts (default 5s can cause ReadTimeout)
            )
        return cls._client
    
    @classmethod
    def close(cls):
        """Close the Qdrant client connection."""
        if cls._client is not None:
            cls._client.close()
            cls._client = None


@lru_cache()
def get_qdrant_client() -> QdrantClient:
    """
    Get Qdrant client instance (singleton).
    
    Returns:
        QdrantClient: Qdrant client instance
    """
    return QdrantClientSingleton.get_client()


# Collection names
PROPERTIES_COLLECTION = "properties"
BUILDER_PROFILES_COLLECTION = "builder_profiles"
BUILDER_SERVICES_COLLECTION = "builder_services"

# Vector dimensions (from all-MiniLM-L6-v2 model)
VECTOR_DIMENSION = 384


async def ensure_collections_exist():
    """
    Ensure all required Qdrant collections exist.
    Creates them if they don't exist.
    """
    import asyncio
    
    client = get_qdrant_client()
    
    collections = [
        (PROPERTIES_COLLECTION, "Property embeddings"),
        (BUILDER_PROFILES_COLLECTION, "Builder profile embeddings"),
        (BUILDER_SERVICES_COLLECTION, "Builder service embeddings"),
    ]
    
    loop = asyncio.get_event_loop()
    
    for collection_name, description in collections:
        try:
            # Check if collection exists (run in executor for async compatibility)
            await loop.run_in_executor(
                None,
                lambda c=collection_name: client.get_collection(c),
            )
            print(f"[QDRANT] Collection '{collection_name}' already exists")
        except Exception:
            # Collection doesn't exist, create it
            await loop.run_in_executor(
                None,
                lambda c=collection_name: client.create_collection(
                    collection_name=c,
                    vectors_config=VectorParams(
                        size=VECTOR_DIMENSION,
                        distance=Distance.COSINE,
                    ),
                ),
            )
            print(f"[QDRANT] Created collection '{collection_name}' ({description})")

