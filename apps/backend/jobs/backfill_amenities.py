"""
Backfill amenity data for existing properties.

Reads properties from Postgres that have lat/lng but no nearby_amenities,
fetches amenities from Overpass, generates Groq summary, saves to Postgres,
and updates Qdrant embeddings + payloads.

Usage (run from apps/backend):
  python -m jobs.backfill_amenities
  python -m jobs.backfill_amenities --limit 50
  python -m jobs.backfill_amenities --skip 100 --batch-size 10
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.db import get_db_session_ctx
from db.models import Property as PropertyModel
from sqlalchemy import select, and_
from services.amenities.service import enrich_property_amenities


async def backfill_amenities(batch_size: int, limit: int | None, skip_rows: int) -> None:
    """Backfill amenities for properties that have coordinates but no amenity data."""
    processed = 0
    skipped = 0
    errors = 0
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 5
    offset = skip_rows

    print(f"[BACKFILL_AMENITIES] Starting backfill: offset={offset}, batch_size={batch_size}, limit={limit}")

    try:
        while True:
            async with get_db_session_ctx() as session:
                # Find properties with lat/lng but no nearby_amenities
                query = (
                    select(PropertyModel)
                    .where(
                        and_(
                            PropertyModel.lat.isnot(None),
                            PropertyModel.lng.isnot(None),
                            PropertyModel.nearby_amenities.is_(None),
                        )
                    )
                    .order_by(PropertyModel.id)
                    .offset(offset)
                    .limit(batch_size)
                )
                result = await session.execute(query)
                rows = result.scalars().all()

            if not rows:
                print("[BACKFILL_AMENITIES] No more properties to process.")
                break

            for row in rows:
                if limit is not None and processed >= limit:
                    print(f"[BACKFILL_AMENITIES] Reached limit {limit}. Stopping.")
                    break

                print(f"[BACKFILL_AMENITIES] Processing {row.id} ({row.city}/{row.area}) [{processed + 1}]")
                try:
                    await enrich_property_amenities(
                        property_id=row.id,
                        lat=row.lat,
                        lon=row.lng,
                        city=row.city or "",
                        area=row.area or "",
                    )
                    processed += 1
                    consecutive_errors = 0  # reset on success
                except Exception as e:
                    print(f"[BACKFILL_AMENITIES] Error on {row.id}: {e}")
                    errors += 1
                    consecutive_errors += 1
                    
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        print(f"[BACKFILL_AMENITIES] Aborting: hit {MAX_CONSECUTIVE_ERRORS} consecutive errors.")
                        print("[BACKFILL_AMENITIES] The Overpass API might be down or heavily throttled.")
                        return

                # Rate limit: Overpass API recommends 1 request every 2-3 seconds for shared servers
                await asyncio.sleep(3.0)

            if limit is not None and processed >= limit:
                break
                
            offset += batch_size
            if len(rows) < batch_size:
                break
                
    except KeyboardInterrupt:
        print("\n[BACKFILL_AMENITIES] Job interrupted by user.")
    except Exception as e:
        print(f"\n[BACKFILL_AMENITIES] Unexpected fatal error: {e}")
    finally:
        print(f"[BACKFILL_AMENITIES] Summary: processed={processed}, skipped={skipped}, errors={errors}")



def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Backfill amenity data for existing properties. Fetches from Overpass, generates Groq summary, updates Postgres and Qdrant."
    )
    p.add_argument("--batch-size", type=int, default=10, help="Number of properties to process per batch (default 10)")
    p.add_argument("--limit", type=int, default=None, help="Max number of properties to process")
    p.add_argument("--skip", type=int, default=0, help="Skip this many properties (resume after failure)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(backfill_amenities(args.batch_size, args.limit, args.skip))


if __name__ == "__main__":
    main()
