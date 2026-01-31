"""
Backfill builder profile embeddings from Postgres into Qdrant.

Reads builder_profiles from Neon PostgreSQL, composes text, generates embeddings,
and upserts to Qdrant with profile_id as UUID string. Run after MongoDB→Postgres
migration so Qdrant payloads use the new UUIDs; builder search then fetches by UUID from Postgres.

Usage (run separately; use --skip to resume):
  cd apps/backend
  python -m jobs.backfill_builder_profile_embeddings
  python -m jobs.backfill_builder_profile_embeddings --skip 100
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.db import get_db_session_ctx
from common.qdrant import ensure_collections_exist
from common.repositories.builder_profile_repository import BuilderProfileRepository
from services.embeddings.compose import compose_builder_profile_text
from services.embeddings.service import embed_batch
from services.vector_search.qdrant_service import upsert_builder_profile_embeddings_batch


async def backfill(batch_size: int, limit: int | None, skip_rows: int) -> None:
    await ensure_collections_exist()
    processed = 0
    skip = skip_rows
    page_size = min(500, batch_size * 4)

    async with get_db_session_ctx() as session:
        repo = BuilderProfileRepository(session)

        while True:
            rows = await repo.list_all(skip=skip, limit=page_size)
            if not rows:
                break

            batch = []
            for doc in rows:
                batch.append(doc)
                if len(batch) >= batch_size:
                    texts = [compose_builder_profile_text(d) for d in batch]
                    vectors = embed_batch(texts)
                    items = []
                    for d, vec in zip(batch, vectors):
                        loc = d.get("location") or {}
                        city = loc.get("city", "") if isinstance(loc, dict) else ""
                        items.append((
                            str(d.get("id") or d.get("_id")),
                            vec,
                            {"company_name": d.get("company_name", ""), "city": city},
                        ))
                    await upsert_builder_profile_embeddings_batch(items)
                    processed += len(batch)
                    print(f"[BACKFILL] Builder profiles: {processed} embeddings upserted to Qdrant")
                    if limit is not None and processed >= limit:
                        print(f"[BACKFILL] Done (limit {limit}). Processed: {processed}")
                        return
                    batch = []

            processed += len(batch)
            if batch:
                texts = [compose_builder_profile_text(d) for d in batch]
                vectors = embed_batch(texts)
                items = []
                for d, vec in zip(batch, vectors):
                    loc = d.get("location") or {}
                    city = loc.get("city", "") if isinstance(loc, dict) else ""
                    items.append((
                        str(d.get("id") or d.get("_id")),
                        vec,
                        {"company_name": d.get("company_name", ""), "city": city},
                    ))
                await upsert_builder_profile_embeddings_batch(items)
                print(f"[BACKFILL] Builder profiles: {processed} embeddings upserted to Qdrant")
                if limit is not None and processed >= limit:
                    print(f"[BACKFILL] Done (limit {limit}). Processed: {processed}")
                    return

            skip += page_size
            if len(rows) < page_size:
                break

    print(f"[BACKFILL] Done. Total builder profiles: {processed}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backfill builder profile embeddings from Postgres to Qdrant (UUID payloads).")
    p.add_argument("--batch-size", type=int, default=50, help="Embedding batch size")
    p.add_argument("--limit", type=int, default=None, help="Max number of profiles to process")
    p.add_argument("--skip", type=int, default=0, help="Skip this many profiles (resume after failure)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(backfill(args.batch_size, args.limit, args.skip))


if __name__ == "__main__":
    main()
