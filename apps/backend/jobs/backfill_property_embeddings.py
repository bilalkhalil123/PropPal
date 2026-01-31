"""
Backfill property embeddings from Postgres into Qdrant.

Reads properties from Neon PostgreSQL, composes text, generates embeddings,
and upserts to Qdrant with property_id as UUID string. Run after MongoDB→Postgres
migration so Qdrant payloads use the new UUIDs; property search then fetches by UUID from Postgres.

Usage (run separately; use --skip to resume after a failure):
  cd apps/backend
  python -m jobs.backfill_property_embeddings
  python -m jobs.backfill_property_embeddings --skip 10900
  python -m jobs.backfill_property_embeddings --batch-size 50 --limit 5000
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.db import get_db_session_ctx
from common.qdrant import ensure_collections_exist
from common.repositories.property_repository import PropertyRepository
from services.embeddings.compose import compose_property_text
from services.embeddings.service import embed_batch
from services.vector_search.qdrant_service import upsert_property_embeddings_batch


async def backfill(batch_size: int, limit: int | None, skip_rows: int) -> None:
    await ensure_collections_exist()
    processed = 0
    skip = skip_rows
    page_size = min(batch_size * 2, 500)

    async with get_db_session_ctx() as session:
        repo = PropertyRepository(session)

        while True:
            rows = await repo.list_all(skip=skip, limit=page_size)
            if not rows:
                break

            batch = []
            for doc in rows:
                batch.append(doc)
                if len(batch) >= batch_size:
                    texts = [compose_property_text(d) for d in batch]
                    vectors = embed_batch(texts)
                    items = [
                        (
                            str(d.get("id") or d.get("_id")),
                            vec,
                            {"city": d.get("city", ""), "price": d.get("price", 0), "property_type": d.get("property_type", "")},
                        )
                        for d, vec in zip(batch, vectors)
                    ]
                    for attempt in range(3):
                        try:
                            await upsert_property_embeddings_batch(items)
                            break
                        except Exception as e:
                            if attempt < 2:
                                wait = 10 * (attempt + 1)
                                print(f"[BACKFILL] Qdrant error, retry in {wait}s: {e}")
                                await asyncio.sleep(wait)
                            else:
                                raise
                    processed += len(batch)
                    print(f"[BACKFILL] Properties: {processed} embeddings upserted to Qdrant")
                    if limit is not None and processed >= limit:
                        print(f"[BACKFILL] Done (limit {limit}). Processed: {processed}")
                        return
                    batch = []

            processed += len(batch)
            if batch:
                texts = [compose_property_text(d) for d in batch]
                vectors = embed_batch(texts)
                items = [
                    (
                        str(d.get("id") or d.get("_id")),
                        vec,
                        {"city": d.get("city", ""), "price": d.get("price", 0), "property_type": d.get("property_type", "")},
                    )
                    for d, vec in zip(batch, vectors)
                ]
                for attempt in range(3):
                    try:
                        await upsert_property_embeddings_batch(items)
                        break
                    except Exception as e:
                        if attempt < 2:
                            wait = 10 * (attempt + 1)
                            print(f"[BACKFILL] Qdrant error, retry in {wait}s: {e}")
                            await asyncio.sleep(wait)
                        else:
                            raise
                print(f"[BACKFILL] Properties: {processed} embeddings upserted to Qdrant")
                if limit is not None and processed >= limit:
                    print(f"[BACKFILL] Done (limit {limit}). Processed: {processed}")
                    return

            skip += page_size
            if len(rows) < page_size:
                break

    print(f"[BACKFILL] Done. Total properties: {processed}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backfill property embeddings from Postgres to Qdrant (UUID payloads). Run separately; use --skip to resume.")
    p.add_argument("--batch-size", type=int, default=50, help="Qdrant upsert batch size (default 50 to avoid 502)")
    p.add_argument("--limit", type=int, default=None, help="Max number of properties to process")
    p.add_argument("--skip", type=int, default=0, help="Skip this many properties (resume after failure)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(backfill(args.batch_size, args.limit, args.skip))


if __name__ == "__main__":
    main()
