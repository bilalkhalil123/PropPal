"""
Reset and backfill Qdrant embeddings using OpenAI embeddings.

Steps:
1) Delete all embeddings from Qdrant (drop & recreate collections).
2) Remove properties not in Lahore/Karachi/Islamabad.
3) Call the cleanup-sold endpoint to remove sold listings.
4) Recreate embeddings for builder profiles, builder services, and remaining properties.

Requires the API to be running for the cleanup-sold endpoint.
Set BACKEND_API_BASE_URL if the API is not at http://{HOST}:{PORT}.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure common module import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from common.config import get_settings
from common.db import get_db_session_ctx
from common.qdrant import (
    get_qdrant_client,
    ensure_collections_exist,
    PROPERTIES_COLLECTION,
    BUILDER_PROFILES_COLLECTION,
    BUILDER_SERVICES_COLLECTION,
)
from common.repositories.property_repository import PropertyRepository
from common.repositories.builder_profile_repository import BuilderProfileRepository
from common.repositories.builder_service_repository import BuilderServiceRepository
from services.embeddings.compose import (
    compose_property_text,
    compose_builder_profile_text,
    compose_builder_services_text,
)
from services.embeddings.service import embed_batch
from services.vector_search.qdrant_service import (
    upsert_property_embeddings_batch,
    upsert_builder_profile_embeddings_batch,
    upsert_builder_service_embeddings_batch,
)


ALLOWED_CITIES = {"lahore", "karachi", "islamabad"}


async def _drop_collections() -> None:
    client = get_qdrant_client()
    loop = asyncio.get_event_loop()
    collections = [
        PROPERTIES_COLLECTION,
        BUILDER_PROFILES_COLLECTION,
        BUILDER_SERVICES_COLLECTION,
    ]
    for name in collections:
        try:
            await loop.run_in_executor(None, lambda n=name: client.delete_collection(n))
        except Exception:
            pass


async def _cleanup_sold_listings(base_url: str) -> None:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(f"{base_url}/api/properties/scraper/cleanup-sold")
        response.raise_for_status()


async def _prune_properties_by_city(repo: PropertyRepository) -> int:
    removed = 0
    skip = 0
    batch_size = 500
    while True:
        rows = await repo.list_all(skip=skip, limit=batch_size)
        if not rows:
            break
        for row in rows:
            city = (row.get("city") or "").strip().lower()
            if city not in ALLOWED_CITIES:
                deleted = await repo.delete(row["id"])
                if deleted:
                    removed += 1
        skip += batch_size
    return removed


async def _backfill_properties(repo: PropertyRepository) -> int:
    processed = 0
    skip = 0
    batch_size = 100
    while True:
        rows = await repo.list_all(skip=skip, limit=batch_size)
        if not rows:
            break
        texts = [compose_property_text(row) for row in rows]
        vectors = embed_batch(texts)
        items = []
        for row, vector in zip(rows, vectors):
            items.append(
                (
                    str(row["id"]),
                    vector,
                    {
                        "db_id": str(row["id"]),
                        "city": row.get("city", ""),
                        "price": row.get("price", 0),
                        "property_type": row.get("property_type", ""),
                    },
                )
            )
        await upsert_property_embeddings_batch(items)
        processed += len(rows)
        skip += batch_size
    return processed


async def _backfill_builder_profiles(repo: BuilderProfileRepository) -> int:
    processed = 0
    skip = 0
    batch_size = 200
    while True:
        rows = await repo.list_all(skip=skip, limit=batch_size)
        if not rows:
            break
        texts = [compose_builder_profile_text(row) for row in rows]
        vectors = embed_batch(texts)
        items = []
        for row, vector in zip(rows, vectors):
            city = (row.get("location") or {}).get("city") if isinstance(row.get("location"), dict) else None
            items.append(
                (
                    str(row["id"]),
                    vector,
                    {
                        "db_id": str(row["id"]),
                        "company_name": row.get("company_name"),
                        "city": city,
                    },
                )
            )
        await upsert_builder_profile_embeddings_batch(items)
        processed += len(rows)
        skip += batch_size
    return processed


async def _backfill_builder_services(repo: BuilderServiceRepository) -> int:
    processed = 0
    skip = 0
    batch_size = 200
    while True:
        rows = await repo.list_all(skip=skip, limit=batch_size)
        if not rows:
            break
        texts = [compose_builder_services_text(row) for row in rows]
        vectors = embed_batch(texts)
        items = []
        for row, vector in zip(rows, vectors):
            items.append(
                (
                    str(row["id"]),
                    vector,
                    {
                        "db_id": str(row["id"]),
                        "category": row.get("category"),
                        "base_price": row.get("base_price"),
                    },
                )
            )
        await upsert_builder_service_embeddings_batch(items)
        processed += len(rows)
        skip += batch_size
    return processed


async def reset_and_backfill() -> None:
    settings = get_settings()
    base_url = os.getenv("BACKEND_API_BASE_URL", f"http://{settings.HOST}:{settings.PORT}")

    print("[RESET] Dropping Qdrant collections...")
    await _drop_collections()
    await ensure_collections_exist()

    async with get_db_session_ctx() as session:
        property_repo = PropertyRepository(session)
        builder_profile_repo = BuilderProfileRepository(session)
        builder_service_repo = BuilderServiceRepository(session)

        removed = await _prune_properties_by_city(property_repo)
        print(f"[RESET] Removed {removed} properties outside target cities")

    print("[RESET] Calling cleanup-sold endpoint...")
    await _cleanup_sold_listings(base_url)

    async with get_db_session_ctx() as session:
        property_repo = PropertyRepository(session)
        builder_profile_repo = BuilderProfileRepository(session)
        builder_service_repo = BuilderServiceRepository(session)

        print("[RESET] Backfilling builder profile embeddings...")
        profiles_count = await _backfill_builder_profiles(builder_profile_repo)
        print(f"[RESET] Builder profiles embedded: {profiles_count}")

        print("[RESET] Backfilling builder service embeddings...")
        services_count = await _backfill_builder_services(builder_service_repo)
        print(f"[RESET] Builder services embedded: {services_count}")

        print("[RESET] Backfilling property embeddings...")
        properties_count = await _backfill_properties(property_repo)
        print(f"[RESET] Properties embedded: {properties_count}")


def main() -> None:
    asyncio.run(reset_and_backfill())


if __name__ == "__main__":
    main()
