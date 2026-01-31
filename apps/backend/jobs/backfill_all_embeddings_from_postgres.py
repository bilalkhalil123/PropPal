"""
Run all embedding backfills from Postgres to Qdrant (UUID payloads).

Run after MongoDB→Postgres migration so Qdrant payloads use the new UUIDs;
property/builder search then fetches by UUID from Postgres.

Runs in order: properties, builder profiles, builder services.

If you hit 502/timeouts, run each backfill separately and use --skip to resume:
  py -m jobs.backfill_property_embeddings --batch-size 50 --skip 10900
  py -m jobs.backfill_builder_profile_embeddings
  py -m jobs.backfill_builder_service_embeddings

Usage:
  cd apps/backend
  python -m jobs.backfill_all_embeddings_from_postgres [--batch-size 50] [--limit N]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import backfill modules and run their backfill functions
from common.qdrant import ensure_collections_exist
from jobs.backfill_property_embeddings import backfill as backfill_properties
from jobs.backfill_builder_profile_embeddings import backfill as backfill_builder_profiles
from jobs.backfill_builder_service_embeddings import backfill as backfill_builder_services


async def run_all(batch_size: int, limit: int | None, skip_properties: int, skip_profiles: int, skip_services: int) -> None:
    print("[BACKFILL] Ensuring Qdrant collections exist...")
    await ensure_collections_exist()
    print("[BACKFILL] 1/3 Properties")
    await backfill_properties(batch_size=batch_size, limit=limit, skip_rows=skip_properties)
    print("[BACKFILL] 2/3 Builder profiles")
    await backfill_builder_profiles(batch_size=min(50, batch_size), limit=limit, skip_rows=skip_profiles)
    print("[BACKFILL] 3/3 Builder services")
    await backfill_builder_services(batch_size=min(50, batch_size), limit=limit, skip_rows=skip_services)
    print("[BACKFILL] All embedding backfills from Postgres completed.")


def main() -> None:
    p = argparse.ArgumentParser(description="Backfill all embeddings from Postgres to Qdrant (UUID payloads). For resume use --skip-* or run each script separately.")
    p.add_argument("--batch-size", type=int, default=50, help="Qdrant batch size (default 50 to avoid 502)")
    p.add_argument("--limit", type=int, default=None, help="Max items per collection (optional)")
    p.add_argument("--skip-properties", type=int, default=0, help="Skip N properties (resume)")
    p.add_argument("--skip-profiles", type=int, default=0, help="Skip N builder profiles (resume)")
    p.add_argument("--skip-services", type=int, default=0, help="Skip N builder services (resume)")
    args = p.parse_args()
    asyncio.run(run_all(args.batch_size, args.limit, args.skip_properties, args.skip_profiles, args.skip_services))


if __name__ == "__main__":
    main()
