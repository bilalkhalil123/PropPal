"""
Expand seller weekly availability into concrete slots and subtract booked visits.

day_of_week on seller_availability: 0 = Monday .. 6 = Sunday (datetime.weekday()).
Slots use BOOKING_TZ (Asia/Karachi) for wall-clock interpretation.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Visit as VisitModel
from db.models import SellerAvailability as SellerAvailabilityModel

BOOKING_TZ = ZoneInfo("Asia/Karachi")
SLOT_MINUTES = 60
STEP_MINUTES = 60
MAX_SLOTS_RETURNED = 12

# Visits that block a time on the calendar (cancelled is free)
_BLOCKING_STATUSES = frozenset({"pending", "confirmed", "completed"})


def _combine_local(d: date, t: time) -> datetime:
    """Naive local wall time in BOOKING_TZ as timezone-aware."""
    naive = datetime.combine(d, t)
    return naive.replace(tzinfo=BOOKING_TZ)


def _iter_candidate_slots(
    rules: List[Dict[str, Any]],
    range_start: date,
    range_end: date,
    slot_minutes: int = SLOT_MINUTES,
    step_minutes: int = STEP_MINUTES,
) -> List[datetime]:
    """Generate sorted unique slot start times from weekly rules."""
    candidates: List[datetime] = []
    delta_day = timedelta(days=1)
    slot_len = timedelta(minutes=slot_minutes)
    step = timedelta(minutes=step_minutes)

    d = range_start
    while d <= range_end:
        dow = d.weekday()
        for rule in rules:
            if int(rule["day_of_week"]) != dow:
                continue
            st = rule["start_time"]
            et = rule["end_time"]
            if isinstance(st, datetime):
                st = st.time()
            if isinstance(et, datetime):
                et = et.time()
            window_start = _combine_local(d, st)
            window_end = _combine_local(d, et)
            if window_end <= window_start:
                continue
            t0 = window_start
            while t0 + slot_len <= window_end:
                candidates.append(t0)
                t0 += step
        d += delta_day

    candidates.sort()
    # dedupe (same instant)
    out: List[datetime] = []
    seen = set()
    for c in candidates:
        key = c.isoformat()
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def _interval_blocks_slot(
    slot_start: datetime,
    slot_end: datetime,
    block_start: datetime,
    block_end: datetime,
) -> bool:
    """Half-open [slot_start, slot_end) vs [block_start, block_end)."""
    return slot_start < block_end and block_start < slot_end


async def _load_booked_intervals(
    session: AsyncSession,
    property_id: str,
    slot_minutes: int = SLOT_MINUTES,
) -> List[Tuple[datetime, datetime]]:
    result = await session.execute(
        select(VisitModel.confirmed_time, VisitModel.status).where(
            VisitModel.property_id == property_id,
            VisitModel.confirmed_time.isnot(None),
        )
    )
    rows = result.all()
    slot_len = timedelta(minutes=slot_minutes)
    intervals: List[Tuple[datetime, datetime]] = []
    for confirmed_time, status in rows:
        if status not in _BLOCKING_STATUSES:
            continue
        if confirmed_time is None:
            continue
        ct = confirmed_time
        if ct.tzinfo is None:
            ct = ct.replace(tzinfo=BOOKING_TZ)
        else:
            ct = ct.astimezone(BOOKING_TZ)
        intervals.append((ct, ct + slot_len))
    return intervals


async def _load_availability_rules(
    session: AsyncSession, seller_id: str, property_id: str
) -> List[Dict[str, Any]]:
    result = await session.execute(
        select(SellerAvailabilityModel)
        .where(SellerAvailabilityModel.seller_id == seller_id)
        .where(SellerAvailabilityModel.property_id == property_id)
    )
    rows = result.scalars().all()
    return [
        {
            "day_of_week": r.day_of_week,
            "start_time": r.start_time,
            "end_time": r.end_time,
        }
        for r in rows
    ]


def _format_label(dt: datetime) -> str:
    """Human-friendly label, e.g. 'Wednesday, March 27, 2026 at 9:00 AM' (12-hour, no leading zero on hour)."""
    local = dt.astimezone(BOOKING_TZ)
    h24 = local.hour
    h12 = h24 % 12
    if h12 == 0:
        h12 = 12
    am_pm = "AM" if h24 < 12 else "PM"
    minute = local.strftime("%M")
    return (
        f"{local.strftime('%A')}, {local.strftime('%B')} {local.day}, {local.year} "
        f"at {h12}:{minute} {am_pm}"
    )


async def compute_available_slots(
    session: AsyncSession,
    seller_id: str,
    property_id: str,
    range_start: date,
    range_end: date,
    max_slots: int = MAX_SLOTS_RETURNED,
) -> Dict[str, Any]:
    rules = await _load_availability_rules(session, seller_id, property_id)
    if not rules:
        return {
            "success": True,
            "slots": [],
            "labels": [],
            "count": 0,
            "message": "No availability rules for this property.",
        }

    candidates = _iter_candidate_slots(rules, range_start, range_end)
    booked = await _load_booked_intervals(session, property_id)
    slot_len = timedelta(minutes=SLOT_MINUTES)

    free: List[datetime] = []
    for c in candidates:
        ce = c + slot_len
        blocked = any(
            _interval_blocks_slot(c, ce, bs, be) for bs, be in booked
        )
        if not blocked:
            free.append(c)
        if len(free) >= max_slots:
            break

    return {
        "success": True,
        "slots": [s.isoformat() for s in free],
        "labels": [_format_label(s) for s in free],
        "count": len(free),
        "message": None,
    }
