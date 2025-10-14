from __future__ import annotations

import argparse
import asyncio
from typing import List
from pymongo import UpdateOne

from motor.motor_asyncio import AsyncIOMotorClient

from common.config import get_settings
from common.db import DatabaseClient
from services.embeddings.compose import compose_property_text
from services.embeddings.service import embed_batch


async def backfill(batch_size: int, limit: int | None) -> None:
    settings = get_settings()
    if DatabaseClient.client is None:
        DatabaseClient.client = AsyncIOMotorClient(settings.MONGODB_URL)
        DatabaseClient.database = DatabaseClient.client[settings.MONGODB_DB_NAME]

    db = DatabaseClient.database
    assert db is not None

    query = {"$or": [{"embedding": {"$exists": False}}, {"embedding": None}]}
    cursor = db["properties"].find(query, projection={
        "title": 1,
        "description": 1,
        "property_type": 1,
        "city": 1,
        "area": 1,
        "bedrooms": 1,
        "bathrooms": 1,
        "area_sqft": 1,
    })

    processed = 0
    batch_docs: List[dict] = []
    async for doc in cursor:
        batch_docs.append(doc)
        if len(batch_docs) >= batch_size:
            await _process_batch(db, batch_docs)
            processed += len(batch_docs)
            batch_docs = []
            if limit is not None and processed >= limit:
                break

    if batch_docs and (limit is None or processed < limit):
        await _process_batch(db, batch_docs)
        processed += len(batch_docs)

    print(f"[BACKFILL] Processed: {processed}")


async def _process_batch(db, docs: List[dict]) -> None:
    texts = [compose_property_text(d) for d in docs]
    vectors = embed_batch(texts)
    ops: List[UpdateOne] = []
    for doc, vec in zip(docs, vectors):
        ops.append(
            UpdateOne({"_id": doc["_id"]}, {"$set": {"embedding": vec}})
        )
    if ops:
        await db["properties"].bulk_write(ops)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--batch-size", type=int, default=100)
    p.add_argument("--limit", type=int, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(backfill(args.batch_size, args.limit))


if __name__ == "__main__":
    main()


