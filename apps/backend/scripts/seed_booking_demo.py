#!/usr/bin/env python3
"""
Seed seller_availability rows for demo visit booking.

Idempotent per property: deletes existing seller_availability for each property, then inserts
Mon–Sat weekly windows (4 blocks per day). Works for any calendar week (e.g. FYP demo Apr 20–26, 2026)
once the booking agent uses that date range via get_available_slots / BOOKING_SLOT_FOCUS_WEEK_* in settings.

Usage (from repo root or apps/backend):
  cd apps/backend && python scripts/seed_booking_demo.py
  cd apps/backend && python scripts/seed_booking_demo.py --limit 5
  cd apps/backend && python scripts/seed_booking_demo.py --city Islamabad
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import time
from pathlib import Path

# apps/backend as import root
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


async def _run(args: argparse.Namespace) -> None:
    from sqlalchemy import delete, select

    from common.db import get_db_session_ctx
    from db.models import Property as PropertyModel
    from db.models import SellerAvailability as SellerAvailabilityModel

    template_blocks = [
        (time(9, 0), time(12, 0)),
        (time(12, 0), time(14, 0)),
        (time(14, 0), time(17, 0)),
        (time(17, 0), time(19, 0)),
    ]
    # Monday=0 .. Saturday=5
    days = range(0, 6)

    async with get_db_session_ctx() as session:
        q = select(PropertyModel)
        if args.city:
            q = q.where(PropertyModel.city.ilike(f"%{args.city.strip()}%"))
        if args.limit is not None:
            q = q.limit(args.limit)
        result = await session.execute(q)
        props = list(result.scalars().all())

        total_rows = 0
        for p in props:
            await session.execute(
                delete(SellerAvailabilityModel).where(
                    SellerAvailabilityModel.property_id == p.id
                )
            )
            for dow in days:
                for start_t, end_t in template_blocks:
                    row = SellerAvailabilityModel(
                        seller_id=p.seller_id,
                        property_id=p.id,
                        day_of_week=dow,
                        start_time=start_t,
                        end_time=end_t,
                    )
                    session.add(row)
                    total_rows += 1

        print(
            f"Seeded seller_availability: {len(props)} properties, "
            f"{total_rows} rows (Mon–Sat, 4 windows/day)."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo seller availability")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of properties to seed",
    )
    parser.add_argument(
        "--city",
        type=str,
        default=None,
        help="Only properties whose city matches (SQL ILIKE %%city%%)",
    )
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
