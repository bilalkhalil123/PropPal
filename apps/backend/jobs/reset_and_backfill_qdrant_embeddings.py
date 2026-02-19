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


def _mask_secret(value: str) -> str:
    if not value:
        return "<not set>"
    if len(value) <= 10:
        return "<hidden>"
    return f"{value[:6]}...{value[-4:]}"


async def _cleanup_sold_listings(base_url: str, timeout_seconds: float) -> None:
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        print(f"{base_url}/api/properties/scraper/cleanup-sold")
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
        print(f"[RESET] Prune progress: scanned {skip} rows, removed {removed}")
    return removed


def _raise_openai_auth_error() -> None:
    raise RuntimeError(
        "OpenAI embedding request failed with 401 Unauthorized. "
        "Check OPENAI_API_KEY in apps/backend/.env and ensure it is valid."
    )


async def _fetch_existing_property_ids() -> set[str]:
    client = get_qdrant_client()
    loop = asyncio.get_event_loop()
    existing: set[str] = set()
    offset = None
    while True:
        def _scroll():
            return client.scroll(
                collection_name=PROPERTIES_COLLECTION,
                limit=200,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

        points, next_offset = await loop.run_in_executor(None, _scroll)
        for point in points or []:
            payload = getattr(point, "payload", None) or {}
            prop_id = payload.get("property_id") or payload.get("db_id")
            if prop_id:
                existing.add(str(prop_id))
        if not next_offset:
            break
        offset = next_offset
    return existing


async def _backfill_properties(repo: PropertyRepository) -> int:
    processed = 0
    skip = 0
    batch_size = 100
    existing_ids = await _fetch_existing_property_ids()
    print(f"[RESET] Existing property embeddings in Qdrant: {len(existing_ids)}")
    while True:
        rows = await repo.list_all(skip=skip, limit=batch_size)
        if not rows:
            break
        missing_rows = [row for row in rows if str(row.get("id")) not in existing_ids]
        if not missing_rows:
            skip += batch_size
            continue
        texts = [compose_property_text(row) for row in missing_rows]
        try:
            vectors = embed_batch(texts)
        except httpx.HTTPStatusError as exc:
            if exc.response is not None and exc.response.status_code == 401:
                _raise_openai_auth_error()
            raise
        items = []
        for row, vector in zip(missing_rows, vectors):
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
        processed += len(missing_rows)
        skip += batch_size
        print(f"[RESET] Property embeddings: {processed} processed")
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
        try:
            vectors = embed_batch(texts)
        except httpx.HTTPStatusError as exc:
            if exc.response is not None and exc.response.status_code == 401:
                _raise_openai_auth_error()
            raise
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
        print(f"[RESET] Builder profiles embeddings: {processed} processed")
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
        try:
            vectors = embed_batch(texts)
        except httpx.HTTPStatusError as exc:
            if exc.response is not None and exc.response.status_code == 401:
                _raise_openai_auth_error()
            raise
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
        print(f"[RESET] Builder services embeddings: {processed} processed")
    return processed


async def reset_and_backfill() -> None:
    settings = get_settings()
    base_url = os.getenv("BACKEND_API_BASE_URL", "http://localhost:8000")
    openai_key = settings.OPENAI_API_KEY or ""

    if not openai_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to apps/backend/.env before running this script."
        )

    await ensure_collections_exist()

    async with get_db_session_ctx() as session:
        property_repo = PropertyRepository(session)
        # removed = await _prune_properties_by_city(property_repo)
        # print(f"[RESET] Removed {removed} properties outside target cities")

    skip_cleanup = os.getenv("SKIP_CLEANUP_SOLD", "false").lower() in {"1", "true", "yes"}
    cleanup_timeout = float(os.getenv("CLEANUP_SOLD_TIMEOUT", "12000"))
    if skip_cleanup:
        print("[RESET] SKIP_CLEANUP_SOLD enabled. Skipping cleanup-sold call.")
    else:
        print(f"[RESET] Calling cleanup-sold endpoint (timeout={cleanup_timeout}s)...")
        try:
            await _cleanup_sold_listings(base_url, cleanup_timeout)
        except Exception as exc:
            print(f"[RESET] cleanup-sold failed or timed out: {exc}. Continuing...")

    async with get_db_session_ctx() as session:
        property_repo = PropertyRepository(session)

        print("[RESET] Backfilling property embeddings (missing only)...")
        properties_count = await _backfill_properties(property_repo)
        print(f"[RESET] Properties embedded: {properties_count}")


def main() -> None:
    asyncio.run(reset_and_backfill())


if __name__ == "__main__":
    main()
