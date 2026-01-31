"""
Visit repository (PostgreSQL/Neon). IDs are UUID strings.
"""

from typing import Any, Dict, List, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import get_db_session
from db.models import Visit as VisitModel


class VisitRepository:
    """Repository for visits (Postgres)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_dict(self, row: VisitModel) -> Dict[str, Any]:
        """Map SQLAlchemy row to API-friendly dict."""
        return {
            "id": row.id,
            "_id": row.id,
            "buyer_id": row.buyer_id,
            "property_id": row.property_id,
            "builder_id": row.builder_id,
            "proposed_time_slots": list(row.proposed_time_slots) if row.proposed_time_slots else [],
            "confirmed_time": row.confirmed_time,
            "status": row.status,
            "agent_notes": row.agent_notes,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    async def get_by_id(self, visit_id: str) -> Optional[Dict[str, Any]]:
        """Get visit by UUID."""
        result = await self.session.execute(
            select(VisitModel).where(VisitModel.id == visit_id)
        )
        row = result.scalar_one_or_none()
        return self._row_to_dict(row) if row else None

    async def list_by_buyer_id(self, buyer_id: str) -> List[Dict[str, Any]]:
        """Get all visits for a buyer."""
        result = await self.session.execute(
            select(VisitModel)
            .where(VisitModel.buyer_id == buyer_id)
            .order_by(VisitModel.created_at.desc())
        )
        rows = result.scalars().all()
        return [self._row_to_dict(r) for r in rows]

    async def list_by_property_id(self, property_id: str) -> List[Dict[str, Any]]:
        """Get all visits for a property."""
        result = await self.session.execute(
            select(VisitModel)
            .where(VisitModel.property_id == property_id)
            .order_by(VisitModel.created_at.desc())
        )
        rows = result.scalars().all()
        return [self._row_to_dict(r) for r in rows]

    async def list_by_builder_id(self, builder_id: str) -> List[Dict[str, Any]]:
        """Get all visits for a builder."""
        result = await self.session.execute(
            select(VisitModel)
            .where(VisitModel.builder_id == builder_id)
            .order_by(VisitModel.created_at.desc())
        )
        rows = result.scalars().all()
        return [self._row_to_dict(r) for r in rows]

    async def create(self, data: Dict[str, Any]) -> VisitModel:
        """Create a visit. Returns the row (with id set)."""
        row = VisitModel(
            buyer_id=data["buyer_id"],
            property_id=data.get("property_id"),
            builder_id=data.get("builder_id"),
            proposed_time_slots=data.get("proposed_time_slots") or [],
            confirmed_time=data.get("confirmed_time"),
            status=data.get("status", "pending"),
            agent_notes=data.get("agent_notes"),
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def update(self, visit_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update visit by id."""
        from datetime import datetime

        result = await self.session.execute(
            select(VisitModel).where(VisitModel.id == visit_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        update_data["updated_at"] = datetime.utcnow()
        for k, v in update_data.items():
            if hasattr(row, k):
                setattr(row, k, v)
        await self.session.flush()
        await self.session.refresh(row)
        return self._row_to_dict(row)

    async def delete(self, visit_id: str) -> bool:
        """Delete visit by id."""
        result = await self.session.execute(
            select(VisitModel).where(VisitModel.id == visit_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True


async def get_visit_repository(
    session: AsyncSession = Depends(get_db_session),
) -> VisitRepository:
    return VisitRepository(session)
