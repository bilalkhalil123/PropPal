"""
Visit repository (PostgreSQL/Neon). IDs are UUID strings.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import get_db_session
from db.models import Property as PropertyModel
from db.models import User as UserModel
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
            "seller_id": getattr(row, "seller_id", None),
            "proposed_time_slots": list(row.proposed_time_slots) if row.proposed_time_slots else [],
            "confirmed_time": row.confirmed_time,
            "status": row.status,
            "agent_notes": row.agent_notes,
            "cancelled_by": getattr(row, "cancelled_by", None),
            "cancellation_reason": getattr(row, "cancellation_reason", None),
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
            seller_id=data.get("seller_id"),
            proposed_time_slots=data.get("proposed_time_slots") or [],
            confirmed_time=data.get("confirmed_time"),
            status=data.get("status", "pending"),
            agent_notes=data.get("agent_notes"),
            cancelled_by=data.get("cancelled_by"),
            cancellation_reason=data.get("cancellation_reason"),
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

    async def find_active_visit_for_buyer_on_property(
        self, buyer_id: str, property_id: str
    ) -> Optional[Dict[str, Any]]:
        """Latest pending or confirmed visit for this buyer on this listing (for reschedule flow)."""
        result = await self.session.execute(
            select(VisitModel)
            .where(
                VisitModel.buyer_id == buyer_id,
                VisitModel.property_id == property_id,
                VisitModel.status.in_(["pending", "confirmed"]),
            )
            .order_by(VisitModel.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return self._row_to_dict(row) if row else None

    def _now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    async def list_upcoming_for_buyer_enriched(
        self, buyer_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Future visits with property title."""
        now = self._now_utc()
        result = await self.session.execute(
            select(VisitModel, PropertyModel.title)
            .outerjoin(PropertyModel, VisitModel.property_id == PropertyModel.id)
            .where(
                VisitModel.buyer_id == buyer_id,
                VisitModel.confirmed_time.isnot(None),
                VisitModel.confirmed_time >= now,
                VisitModel.status.in_(["pending", "confirmed"]),
            )
            .order_by(VisitModel.confirmed_time.asc())
            .limit(limit)
        )
        out: List[Dict[str, Any]] = []
        for visit, title in result.all():
            d = self._row_to_dict(visit)
            d["property_title"] = title or "Property"
            out.append(d)
        return out

    async def list_upcoming_for_seller_enriched(
        self, seller_user_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Future visits on listings this user sells, with property title and buyer name."""
        now = self._now_utc()
        result = await self.session.execute(
            select(VisitModel, PropertyModel.title, UserModel.name)
            .outerjoin(PropertyModel, VisitModel.property_id == PropertyModel.id)
            .outerjoin(UserModel, VisitModel.buyer_id == UserModel.id)
            .where(
                VisitModel.confirmed_time.isnot(None),
                VisitModel.confirmed_time >= now,
                VisitModel.status.in_(["pending", "confirmed"]),
                or_(
                    VisitModel.seller_id == seller_user_id,
                    PropertyModel.seller_id == seller_user_id,
                ),
            )
            .order_by(VisitModel.confirmed_time.asc())
            .limit(limit)
        )
        out: List[Dict[str, Any]] = []
        for visit, title, buyer_name in result.all():
            d = self._row_to_dict(visit)
            d["property_title"] = title or "Property"
            d["buyer_name"] = buyer_name or "Buyer"
            out.append(d)
        return out


async def get_visit_repository(
    session: AsyncSession = Depends(get_db_session),
) -> VisitRepository:
    return VisitRepository(session)
