"""
Server-side calendar text injected into the booking agent system prompt.

Stops wrong years (e.g. 2024) and wrong weekdays (e.g. Friday vs Thursday) by giving
explicit day → YYYY-MM-DD mapping from a trusted clock (Asia/Karachi).

Optional BOOKING_CALENDAR_ANCHOR_DATE overrides "today" for demos.
Optional BOOKING_SLOT_FOCUS_WEEK_* defines the default tour week (FYP: 20–26 Apr 2026).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from services.booking.slots import BOOKING_TZ


def format_booking_calendar_context(settings: Any) -> str:
    anchor_raw = (getattr(settings, "BOOKING_CALENDAR_ANCHOR_DATE", None) or "").strip()
    if anchor_raw:
        try:
            today = date.fromisoformat(anchor_raw[:10])
        except ValueError:
            today = datetime.now(BOOKING_TZ).date()
    else:
        today = datetime.now(BOOKING_TZ).date()

    lines = [
        "=== CALENDAR (server truth — follow exactly; never invent 2024 or wrong weekdays) ===",
        f"REFERENCE_TODAY: {today.isoformat()} — {today.strftime('%A')}, {today.strftime('%B')} {today.day}, {today.year} (Asia/Karachi).",
        "When the user names a weekday only, map it to the matching date below, then call get_available_slots(start,end) with a range that includes ONLY that calendar day for a single-day pull, or a tight range around it.",
        "Next 14 days (weekday → ISO date):",
    ]
    for i in range(14):
        d = today + timedelta(days=i)
        lines.append(f"  {d.strftime('%A')}: {d.isoformat()}")

    fs = (getattr(settings, "BOOKING_SLOT_FOCUS_WEEK_START", None) or "").strip()
    fe = (getattr(settings, "BOOKING_SLOT_FOCUS_WEEK_END", None) or "").strip()
    if fs and fe:
        lines.append(
            f"Primary tour week (use for vague requests like 'this week' for demos): "
            f"get_available_slots('{fs}','{fe}'). "
            f"If they say a weekday, ensure the slots you show are for THAT weekday inside this span "
            f"(e.g. Friday must be the Friday between {fs} and {fe}, not Thursday)."
        )

    lines.append(
        "If their weekday is ambiguous across two weeks, ask one short clarifying question OR use the single date line from the 14-day list that matches 'next' that weekday."
    )
    return "\n".join(lines)
