"""
Precompute open slots for the configured focus week and format for the booking system prompt.

Lets the agent answer many slot questions without calling get_available_slots (saves one LLM+tool round).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from services.booking.slots import compute_available_slots


async def format_preloaded_focus_week_slots(
    session: AsyncSession,
    seller_id: str,
    property_id: str,
    settings: Any,
    max_slots: int = 14,
) -> str:
    fs = (getattr(settings, "BOOKING_SLOT_FOCUS_WEEK_START", None) or "").strip()
    fe = (getattr(settings, "BOOKING_SLOT_FOCUS_WEEK_END", None) or "").strip()
    if not fs or not fe:
        return ""
    try:
        d0 = date.fromisoformat(fs[:10])
        d1 = date.fromisoformat(fe[:10])
    except ValueError:
        return ""

    data = await compute_available_slots(
        session, seller_id, property_id, d0, d1, max_slots=max_slots
    )
    slots = data.get("slots") or []
    labels = data.get("labels") or []
    if not slots:
        return (
            f"=== PRELOADED_AVAILABLE_SLOTS ({fs} to {fe}) ===\n"
            "No open slots in this window (or no seller rules). Call get_available_slots for another range.\n"
        )

    iso_lines = [f"{i + 1}: {iso}" for i, iso in enumerate(slots)]
    label_lines = [f"{i + 1}. {lab}" for i, lab in enumerate(labels)]
    return (
        f"=== PRELOADED_AVAILABLE_SLOTS ({fs} to {fe}) ===\n"
        "For requests about days/times inside this date range, use ONLY this list—do NOT call get_available_slots "
        "for the same range (saves time). Show users the numbered labels (no raw ISO in chat). "
        "For create_visit_booking / reschedule_visit, copy the ISO from the matching line below.\n"
        "ISO by option number:\n"
        + "\n".join(iso_lines)
        + "\nHuman-friendly labels (same order):\n"
        + "\n".join(label_lines)
        + "\nIf the user needs dates OUTSIDE this range, or asks to refresh, call get_available_slots(start,end).\n"
    )
