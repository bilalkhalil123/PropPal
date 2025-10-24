from __future__ import annotations

import asyncio

from motor.motor_asyncio import AsyncIOMotorClient

from common.config import get_settings
from common.db import DatabaseClient


async def create_index() -> None:
    settings = get_settings()
    if DatabaseClient.client is None:
        DatabaseClient.client = AsyncIOMotorClient(settings.MONGODB_URL)
        DatabaseClient.database = DatabaseClient.client[settings.MONGODB_DB_NAME]

    db = DatabaseClient.database
    assert db is not None

    # See Atlas docs: createSearchIndexes command
    # Atlas Vector Search requires type: knnVector and dimensions: <int>
    index_definition = {
        "mappings": {
            "dynamic": True,
            "fields": {
                "embedding": {
                    "type": "knnVector",
                    "dimensions": 384,
                    "similarity": "cosine",
                }
            },
        }
    }

    cmd = {
        "createSearchIndexes": "properties",
        "indexes": [
            {"name": "properties_embedding_index", "definition": index_definition}
        ],
    }

    try:
        res = await db.command(cmd)
        print("[VECTOR-INDEX]", res)
    except Exception as e:
        print("[VECTOR-INDEX][ERROR]", e)


def main() -> None:
    asyncio.run(create_index())


if __name__ == "__main__":
    main()


