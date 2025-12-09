"""
Migration script to backfill existing embeddings from MongoDB to Qdrant.

This script reads all existing embeddings from MongoDB collections and
stores them in Qdrant for vector search.

Usage:
    python -m jobs.migrate_to_qdrant
    python -m jobs.migrate_to_qdrant --collection properties
    python -m jobs.migrate_to_qdrant --collection builder_profiles
    python -m jobs.migrate_to_qdrant --collection builder_services
"""

from __future__ import annotations

import argparse
import asyncio
from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

from common.config import get_settings
from common.db import DatabaseClient
from common.qdrant import ensure_collections_exist
from services.vector_search.qdrant_service import (
    upsert_property_embedding,
    upsert_builder_profile_embedding,
    upsert_builder_service_embedding,
)


async def migrate_properties(batch_size: int = 100) -> None:
    """Migrate property embeddings from MongoDB to Qdrant."""
    settings = get_settings()
    if DatabaseClient.client is None:
        DatabaseClient.client = AsyncIOMotorClient(settings.MONGODB_URL)
        DatabaseClient.database = DatabaseClient.client[settings.MONGODB_DB_NAME]

    db = DatabaseClient.database
    assert db is not None

    print("[MIGRATE] Starting property embeddings migration...")
    
    # Find all properties with embeddings
    query = {"embedding": {"$exists": True, "$ne": None}}
    cursor = db["properties"].find(query, {
        "_id": 1,
        "embedding": 1,
        "city": 1,
        "price": 1,
        "property_type": 1,
    })

    processed = 0
    batch: List[dict] = []
    
    async for doc in cursor:
        batch.append(doc)
        if len(batch) >= batch_size:
            await _process_property_batch(batch)
            processed += len(batch)
            batch = []
            print(f"[MIGRATE] Processed {processed} properties...")

    if batch:
        await _process_property_batch(batch)
        processed += len(batch)

    print(f"[MIGRATE] Completed property migration: {processed} properties migrated")


async def _process_property_batch(batch: List[dict]) -> None:
    """Process a batch of properties and store in Qdrant."""
    for doc in batch:
        property_id = str(doc["_id"])
        embedding = doc.get("embedding")
        
        if not embedding:
            continue
            
        metadata = {
            "city": doc.get("city", ""),
            "price": doc.get("price", 0),
            "property_type": doc.get("property_type", ""),
        }
        
        await upsert_property_embedding(
            property_id=property_id,
            embedding=embedding,
            metadata=metadata,
        )


async def migrate_builder_profiles(batch_size: int = 100) -> None:
    """Migrate builder profile embeddings from MongoDB to Qdrant."""
    settings = get_settings()
    if DatabaseClient.client is None:
        DatabaseClient.client = AsyncIOMotorClient(settings.MONGODB_URL)
        DatabaseClient.database = DatabaseClient.client[settings.MONGODB_DB_NAME]

    db = DatabaseClient.database
    assert db is not None

    print("[MIGRATE] Starting builder profile embeddings migration...")
    
    # Find all builder profiles with embeddings
    query = {"embeddings": {"$exists": True, "$ne": None}}
    cursor = db["builder_profiles"].find(query, {
        "_id": 1,
        "embeddings": 1,
        "company_name": 1,
        "location": 1,
    })

    processed = 0
    batch: List[dict] = []
    
    async for doc in cursor:
        batch.append(doc)
        if len(batch) >= batch_size:
            await _process_profile_batch(batch)
            processed += len(batch)
            batch = []
            print(f"[MIGRATE] Processed {processed} builder profiles...")

    if batch:
        await _process_profile_batch(batch)
        processed += len(batch)

    print(f"[MIGRATE] Completed builder profile migration: {processed} profiles migrated")


async def _process_profile_batch(batch: List[dict]) -> None:
    """Process a batch of builder profiles and store in Qdrant."""
    for doc in batch:
        profile_id = str(doc["_id"])
        embedding = doc.get("embeddings")
        
        if not embedding:
            continue
            
        location = doc.get("location", {})
        city = location.get("city", "") if isinstance(location, dict) else ""
        
        metadata = {
            "company_name": doc.get("company_name", ""),
            "city": city,
        }
        
        await upsert_builder_profile_embedding(
            profile_id=profile_id,
            embedding=embedding,
            metadata=metadata,
        )


async def migrate_builder_services(batch_size: int = 100) -> None:
    """Migrate builder service embeddings from MongoDB to Qdrant."""
    settings = get_settings()
    if DatabaseClient.client is None:
        DatabaseClient.client = AsyncIOMotorClient(settings.MONGODB_URL)
        DatabaseClient.database = DatabaseClient.client[settings.MONGODB_DB_NAME]

    db = DatabaseClient.database
    assert db is not None

    print("[MIGRATE] Starting builder service embeddings migration...")
    
    # Find all builder services with embeddings
    query = {"embeddings": {"$exists": True, "$ne": None}}
    cursor = db["builder_services"].find(query, {
        "_id": 1,
        "embeddings": 1,
        "service_name": 1,
        "category": 1,
        "builder_id": 1,
    })

    processed = 0
    batch: List[dict] = []
    
    async for doc in cursor:
        batch.append(doc)
        if len(batch) >= batch_size:
            await _process_service_batch(batch)
            processed += len(batch)
            batch = []
            print(f"[MIGRATE] Processed {processed} builder services...")

    if batch:
        await _process_service_batch(batch)
        processed += len(batch)

    print(f"[MIGRATE] Completed builder service migration: {processed} services migrated")


async def _process_service_batch(batch: List[dict]) -> None:
    """Process a batch of builder services and store in Qdrant."""
    for doc in batch:
        service_id = str(doc["_id"])
        embedding = doc.get("embeddings")
        
        if not embedding:
            continue
            
        builder_id = doc.get("builder_id")
        builder_id_str = str(builder_id) if builder_id else ""
        
        metadata = {
            "service_name": doc.get("service_name", ""),
            "category": doc.get("category", ""),
            "builder_id": builder_id_str,
        }
        
        await upsert_builder_service_embedding(
            service_id=service_id,
            embedding=embedding,
            metadata=metadata,
        )


async def main(collection: Optional[str] = None, batch_size: int = 100) -> None:
    """Main migration function."""
    print("[MIGRATE] Initializing Qdrant collections...")
    await ensure_collections_exist()
    
    if collection is None or collection == "properties":
        await migrate_properties(batch_size)
    
    if collection is None or collection == "builder_profiles":
        await migrate_builder_profiles(batch_size)
    
    if collection is None or collection == "builder_services":
        await migrate_builder_services(batch_size)
    
    print("[MIGRATE] Migration completed!")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate embeddings from MongoDB to Qdrant")
    parser.add_argument(
        "--collection",
        type=str,
        choices=["properties", "builder_profiles", "builder_services"],
        default=None,
        help="Specific collection to migrate (default: all collections)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for processing (default: 100)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.collection, args.batch_size))

