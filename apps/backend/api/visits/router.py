from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import get_db_session
from common.repositories.visit_repository import VisitRepository
from models.users import User
from services.auth.utils import get_current_user

router = APIRouter(prefix="/api/visits", tags=["visits"])


def _visit_json(v: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(v)
    ct = out.get("confirmed_time")
    if hasattr(ct, "isoformat"):
        out["confirmed_time"] = ct.isoformat()
    for k in ("created_at", "updated_at"):
        t = out.get(k)
        if hasattr(t, "isoformat"):
            out[k] = t.isoformat()
    return out


@router.get("/me/upcoming", summary="Buyer's upcoming property visits")
async def buyer_upcoming_visits(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, List[Dict[str, Any]]]:
    repo = VisitRepository(session)
    rows = await repo.list_upcoming_for_buyer_enriched(current_user.id)
    return {"visits": [_visit_json(v) for v in rows]}


@router.get("/seller/upcoming", summary="Seller's upcoming visits on their listings")
async def seller_upcoming_visits(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, List[Dict[str, Any]]]:
    repo = VisitRepository(session)
    rows = await repo.list_upcoming_for_seller_enriched(current_user.id)
    return {"visits": [_visit_json(v) for v in rows]}
