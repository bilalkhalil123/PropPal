"""
Initialize Qdrant collections for vector search.

This script creates the required Qdrant collections if they don't exist.

Usage:
    python -m jobs.init_qdrant_collections
"""

from __future__ import annotations

import asyncio

from common.qdrant import ensure_collections_exist


async def main() -> None:
    """Initialize all Qdrant collections."""
    print("[INIT] Initializing Qdrant collections...")
    await ensure_collections_exist()
    print("[INIT] Qdrant collections initialized successfully!")


if __name__ == "__main__":
    asyncio.run(main())

