"""
LangChain tools for property visit booking. Built per request with buyer/property/seller closure.
Uses get_db_session_ctx + thread/async pattern like property_search_tool.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from common.db import get_db_session_ctx
from common.repositories.property_repository import PropertyRepository
from common.repositories.visit_repository import VisitRepository
from services.booking.slots import BOOKING_TZ, compute_available_slots

logger = logging.getLogger(__name__)


def _run_async(coro):
    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        return asyncio.run(coro)


def _parse_iso_datetime(s: str) -> datetime:
    s = (s or "").strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BOOKING_TZ)
    return dt


def _parse_iso_date(s: str) -> date:
    return date.fromisoformat((s or "").strip()[:10])


def build_booking_tools(buyer_id: str, property_id: str, seller_id: str) -> List:
    """Return LangChain tools bound to this booking context."""

    async def _get_property_context_async() -> Dict[str, Any]:
        async with get_db_session_ctx() as session:
            repo = PropertyRepository(session)
            row = await repo.get_by_id(property_id)
            if not row:
                return {
                    "success": False,
                    "error": "Property not found",
                    "summary_for_llm": "Property not found.",
                }
            addr = f"{row.get('area', '')}, {row.get('city', '')}".strip(", ")
            return {
                "success": True,
                "property_id": row["id"],
                "title": row.get("title"),
                "city": row.get("city"),
                "area": row.get("area"),
                "address_line": addr,
                "seller_id": row.get("seller_id"),
                "summary_for_llm": (
                    f"Property: {row.get('title')}. Location: {addr}. "
                    f"seller_id={row.get('seller_id')}."
                ),
            }

    async def _get_slots_async(range_start: str, range_end: str) -> Dict[str, Any]:
        try:
            d0 = _parse_iso_date(range_start)
            d1 = _parse_iso_date(range_end)
        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "summary_for_llm": "Invalid date format; use YYYY-MM-DD.",
            }
        if d1 < d0:
            d0, d1 = d1, d0
        async with get_db_session_ctx() as session:
            out = await compute_available_slots(
                session, seller_id, property_id, d0, d1
            )
        slots = out.get("slots") or []
        labels = out.get("labels") or []
        if not slots:
            msg = out.get("message") or "No open slots in that range."
            return {
                "success": True,
                "slots": [],
                "labels": [],
                "summary_for_llm": msg,
            }
        lines = [f"{i + 1}. {lab}" for i, lab in enumerate(labels)]
        summary_for_llm = (
            "Available visit slots — show the user ONLY the numbered list below. "
            "Use friendly wording; do NOT show ISO timestamps or strings like 2024-03-27T... to the user.\n\n"
            + "\n".join(lines)
            + "\n\nWhen the user chooses an option by number or time, call create_visit_booking with "
            "confirmed_slot_iso set to the matching entry from the `slots` array "
            "(option 1 = slots[0], option 2 = slots[1], etc.). Copy the ISO string exactly."
        )
        return {
            "success": True,
            "slots": slots,
            "labels": labels,
            "summary_for_llm": summary_for_llm,
        }

    async def _create_visit_async(
        confirmed_slot_iso: str, notes: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            ct = _parse_iso_datetime(confirmed_slot_iso)
        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "summary_for_llm": "Could not parse date/time for the visit.",
            }
        async with get_db_session_ctx() as session:
            repo = VisitRepository(session)
            active = await repo.find_active_visit_for_buyer_on_property(
                buyer_id, property_id
            )
            if active:
                return {
                    "success": False,
                    "summary_for_llm": (
                        f"Buyer already has visit id={active.get('id')} (status {active.get('status')}) "
                        "on this listing. Use reschedule_visit with that visit_id and a slot from "
                        "get_available_slots, or cancel_visit first—do not create a second booking."
                    ),
                }
            row = await repo.create(
                {
                    "buyer_id": buyer_id,
                    "property_id": property_id,
                    "seller_id": seller_id,
                    "confirmed_time": ct,
                    "status": "pending",
                    "agent_notes": (notes or "").strip() or None,
                    "proposed_time_slots": [],
                }
            )
            d = repo._row_to_dict(row)
        visit = {
            "id": d["id"],
            "buyer_id": d["buyer_id"],
            "property_id": d["property_id"],
            "seller_id": d["seller_id"],
            "confirmed_time": d["confirmed_time"].isoformat() if d["confirmed_time"] else None,
            "status": d["status"],
            "agent_notes": d["agent_notes"],
        }
        return {
            "success": True,
            "visit": visit,
            "summary_for_llm": (
                f"Created pending visit booking id={visit['id']} at {visit['confirmed_time']}."
            ),
        }

    async def _confirm_visit_async(visit_id: str) -> Dict[str, Any]:
        async with get_db_session_ctx() as session:
            repo = VisitRepository(session)
            existing = await repo.get_by_id(visit_id)
            if not existing or existing.get("buyer_id") != buyer_id:
                return {
                    "success": False,
                    "summary_for_llm": "Visit not found or not yours.",
                }
            updated = await repo.update(visit_id, {"status": "confirmed"})
        if not updated:
            return {"success": False, "summary_for_llm": "Could not confirm visit."}
        return {
            "success": True,
            "visit": updated,
            "summary_for_llm": f"Visit {visit_id} is confirmed.",
        }

    async def _cancel_visit_async(visit_id: str, reason: str) -> Dict[str, Any]:
        async with get_db_session_ctx() as session:
            repo = VisitRepository(session)
            existing = await repo.get_by_id(visit_id)
            if not existing or existing.get("buyer_id") != buyer_id:
                return {
                    "success": False,
                    "summary_for_llm": "Visit not found or not yours.",
                }
            updated = await repo.update(
                visit_id,
                {
                    "status": "cancelled",
                    "cancelled_by": buyer_id,
                    "cancellation_reason": (reason or "").strip() or None,
                },
            )
        if not updated:
            return {"success": False, "summary_for_llm": "Could not cancel visit."}
        return {
            "success": True,
            "visit": updated,
            "summary_for_llm": f"Visit {visit_id} cancelled.",
        }

    async def _reschedule_visit_async(
        visit_id: str, new_slot_iso: str
    ) -> Dict[str, Any]:
        try:
            ct = _parse_iso_datetime(new_slot_iso)
        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "summary_for_llm": "Invalid new slot time.",
            }
        async with get_db_session_ctx() as session:
            repo = VisitRepository(session)
            existing = await repo.get_by_id(visit_id)
            if not existing or existing.get("buyer_id") != buyer_id:
                return {
                    "success": False,
                    "summary_for_llm": "Visit not found or not yours.",
                }
            updated = await repo.update(
                visit_id,
                {
                    "confirmed_time": ct,
                    "status": "pending",
                },
            )
        if not updated:
            return {"success": False, "summary_for_llm": "Could not reschedule."}
        return {
            "success": True,
            "visit": updated,
            "summary_for_llm": f"Visit rescheduled to {updated.get('confirmed_time')}.",
        }

    async def _get_user_visits_async(
        filter_property_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        async with get_db_session_ctx() as session:
            repo = VisitRepository(session)
            rows = await repo.list_by_buyer_id(buyer_id)
        if filter_property_id:
            rows = [r for r in rows if r.get("property_id") == filter_property_id]
        lines = []
        for r in rows[:15]:
            st = r.get("status")
            ct = r.get("confirmed_time")
            pid = r.get("property_id")
            lines.append(
                f"id={r.get('id')} property={pid} status={st} time={ct}"
            )
        summary = "Your visits:\n" + "\n".join(lines) if lines else "No visits found."
        return {
            "success": True,
            "visits": rows[:15],
            "summary_for_llm": summary,
        }

    async def _append_notes_async(visit_id: str, note_text: str) -> Dict[str, Any]:
        note_text = (note_text or "").strip()
        if not note_text:
            return {"success": False, "summary_for_llm": "Note text empty."}
        async with get_db_session_ctx() as session:
            repo = VisitRepository(session)
            existing = await repo.get_by_id(visit_id)
            if not existing or existing.get("buyer_id") != buyer_id:
                return {
                    "success": False,
                    "summary_for_llm": "Visit not found or not yours.",
                }
            prev = (existing.get("agent_notes") or "").strip()
            merged = f"{prev}\n{note_text}".strip() if prev else note_text
            updated = await repo.update(visit_id, {"agent_notes": merged})
        if not updated:
            return {"success": False, "summary_for_llm": "Could not update notes."}
        return {
            "success": True,
            "visit": updated,
            "summary_for_llm": "Notes updated for the visit.",
        }

    @tool
    def get_property_context() -> str:
        """Load the current property title, location, and seller_id from the database."""
        return json.dumps(_run_async(_get_property_context_async()), default=str)

    @tool
    def get_available_slots(date_range_start: str, date_range_end: str) -> str:
        """
        List free visit slots between two calendar dates (YYYY-MM-DD).
        Call this whenever the user mentions a day, date, or week—before you offer or assume any time.
        After this returns, show the user the numbered list and wait until they pick a specific time before create_visit_booking.
        """
        return json.dumps(
            _run_async(_get_slots_async(date_range_start, date_range_end)),
            default=str,
        )

    @tool
    def create_visit_booking(confirmed_slot_iso: str, notes: str = "") -> str:
        """
        Create a pending visit ONLY after the user explicitly chose a time that matches a slot from get_available_slots.
        Do NOT call when the user only said a weekday or vague window without picking a listed time.
        Pass the exact ISO from the matching entry in the slots array. Optional buyer notes.
        """
        return json.dumps(
            _run_async(_create_visit_async(confirmed_slot_iso, notes or None)),
            default=str,
        )

    @tool
    def confirm_visit(visit_id: str) -> str:
        """
        Set status to confirmed ONLY after the user clearly says yes / confirm / go ahead.
        Never call in the same turn as create_visit_booking; wait for their explicit confirmation reply.
        """
        return json.dumps(_run_async(_confirm_visit_async(visit_id)), default=str)

    @tool
    def cancel_visit(visit_id: str, reason: str) -> str:
        """Cancel a visit; reason is stored for the seller."""
        return json.dumps(_run_async(_cancel_visit_async(visit_id, reason)), default=str)

    @tool
    def reschedule_visit(visit_id: str, new_slot_iso: str) -> str:
        """
        Move an existing visit to a new instant. Use when they already have a pending visit and pick a new time.
        new_slot_iso must match a slot from get_available_slots for the target day.
        """
        return json.dumps(
            _run_async(_reschedule_visit_async(visit_id, new_slot_iso)),
            default=str,
        )

    @tool
    def get_user_visits(only_this_property: str = "yes") -> str:
        """
        List this buyer's visits. Pass only_this_property=yes to restrict to the current listing (default), or no for all properties.
        """
        v = (only_this_property or "yes").strip().lower()
        fid = property_id if v in ("yes", "true", "1", "") else None
        return json.dumps(_run_async(_get_user_visits_async(fid)), default=str)

    @tool
    def append_visit_notes(visit_id: str, note_text: str) -> str:
        """Append a line to visit notes (e.g. 'please show the terrace')."""
        return json.dumps(_run_async(_append_notes_async(visit_id, note_text)), default=str)

    return [
        get_property_context,
        get_available_slots,
        create_visit_booking,
        confirm_visit,
        cancel_visit,
        reschedule_visit,
        get_user_visits,
        append_visit_notes,
    ]
