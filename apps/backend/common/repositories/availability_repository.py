"""
Availability repository (PostgreSQL/Neon). IDs are UUID strings.
"""

from typing import Any, Dict, List, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import get_db_session
from db.models import Availability as AvailabilityModel


class AvailabilityRepository:
    """Repository for availability (Postgres)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_dict(self, row: AvailabilityModel) -> Dict[str, Any]:
        """Map SQLAlchemy row to API-friendly dict."""
        return {
            "id": row.id,
            "_id": row.id,
            "property_id": row.property_id,
            "seller_id": row.seller_id,
            "slots": row.slots or {},
        }

    async def get_by_id(self, availability_id: str) -> Optional[Dict[str, Any]]:
        """Get availability by UUID."""
        result = await self.session.execute(
            select(AvailabilityModel).where(AvailabilityModel.id == availability_id)
        )
        row = result.scalar_one_or_none()
        return self._row_to_dict(row) if row else None

    async def get_by_property_id(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Get availability for a property."""
        result = await self.session.execute(
            select(AvailabilityModel).where(AvailabilityModel.property_id == property_id)
        )
        row = result.scalar_one_or_none()
        return self._row_to_dict(row) if row else None

    async def get_by_seller_id(self, seller_id: str) -> List[Dict[str, Any]]:
        """Get all availability records for a seller."""
        result = await self.session.execute(
            select(AvailabilityModel).where(AvailabilityModel.seller_id == seller_id)
        )
        rows = result.scalars().all()
        return [self._row_to_dict(r) for r in rows]

    async def create(self, data: Dict[str, Any]) -> AvailabilityModel:
        """Create an availability record. Returns the row (with id set)."""
        row = AvailabilityModel(
            property_id=data.get("property_id"),
            seller_id=data.get("seller_id"),
            slots=data.get("slots"),
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def update(self, availability_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update availability by id."""
        result = await self.session.execute(
            select(AvailabilityModel).where(AvailabilityModel.id == availability_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        for k, v in update_data.items():
            if hasattr(row, k):
                setattr(row, k, v)
        await self.session.flush()
        await self.session.refresh(row)
        return self._row_to_dict(row)

    async def delete(self, availability_id: str) -> bool:
        """Delete availability by id."""
        result = await self.session.execute(
            select(AvailabilityModel).where(AvailabilityModel.id == availability_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True


async def get_availability_repository(
    session: AsyncSession = Depends(get_db_session),
) -> AvailabilityRepository:
    return AvailabilityRepository(session)
