"""
Builder service repository (PostgreSQL/Neon). IDs are UUID strings.
"""

from typing import Any, Dict, List, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import get_db_session
from db.models import BuilderService as BuilderServiceModel


class BuilderServiceRepository:
    """Repository for builder_services (Postgres)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_dict(self, row: BuilderServiceModel) -> Dict[str, Any]:
        """Map SQLAlchemy row to API-friendly dict."""
        return {
            "id": row.id,
            "_id": row.id,
            "builder_id": row.builder_id,
            "title": row.title,
            "description": row.description,
            "category": row.category,
            "base_price": row.base_price,
            "price_unit": row.price_unit,
            "estimated_duration": row.estimated_duration,
            "service_features": list(row.service_features) if row.service_features else [],
            "service_images": list(row.service_images) if row.service_images else [],
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    async def get_by_id(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get builder service by UUID."""
        result = await self.session.execute(
            select(BuilderServiceModel).where(BuilderServiceModel.id == service_id)
        )
        row = result.scalar_one_or_none()
        return self._row_to_dict(row) if row else None

    async def list_by_builder_id(self, builder_id: str) -> List[Dict[str, Any]]:
        """Get all services for a builder."""
        result = await self.session.execute(
            select(BuilderServiceModel)
            .where(BuilderServiceModel.builder_id == builder_id)
            .order_by(BuilderServiceModel.created_at.desc())
        )
        rows = result.scalars().all()
        return [self._row_to_dict(r) for r in rows]

    async def create(self, data: Dict[str, Any]) -> BuilderServiceModel:
        """Create a builder service. Returns the row (with id set)."""
        row = BuilderServiceModel(
            builder_id=data["builder_id"],
            title=data["title"],
            description=data["description"],
            category=data["category"],
            base_price=data["base_price"],
            price_unit=data["price_unit"],
            estimated_duration=data.get("estimated_duration"),
            service_features=data.get("service_features"),
            service_images=data.get("service_images"),
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def update(self, service_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update builder service by id."""
        from datetime import datetime

        result = await self.session.execute(
            select(BuilderServiceModel).where(BuilderServiceModel.id == service_id)
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

    async def delete(self, service_id: str) -> bool:
        """Delete builder service by id."""
        result = await self.session.execute(
            select(BuilderServiceModel).where(BuilderServiceModel.id == service_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True

    async def delete_by_builder_id(self, builder_id: str) -> int:
        """Delete all services for a builder. Returns count deleted."""
        result = await self.session.execute(
            select(BuilderServiceModel).where(BuilderServiceModel.builder_id == builder_id)
        )
        rows = result.scalars().all()
        for row in rows:
            await self.session.delete(row)
        await self.session.flush()
        return len(rows)

    async def list_by_ids(self, service_ids: List[str]) -> List[Dict[str, Any]]:
        """Get multiple services by UUIDs."""
        if not service_ids:
            return []
        result = await self.session.execute(
            select(BuilderServiceModel).where(BuilderServiceModel.id.in_(service_ids))
        )
        rows = result.scalars().all()
        return [self._row_to_dict(r) for r in rows]

    async def list_all(self, skip: int = 0, limit: int = 5000) -> List[Dict[str, Any]]:
        """List all builder services with pagination (for embedding backfill)."""
        result = await self.session.execute(
            select(BuilderServiceModel)
            .order_by(BuilderServiceModel.id)
            .offset(skip)
            .limit(limit)
        )
        rows = result.scalars().all()
        return [self._row_to_dict(r) for r in rows]


async def get_builder_service_repository(
    session: AsyncSession = Depends(get_db_session),
) -> BuilderServiceRepository:
    return BuilderServiceRepository(session)
