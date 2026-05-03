"""
Builder bid repository (PostgreSQL/Neon). IDs are UUID strings.
"""

from typing import Any, Dict, List, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import get_db_session
from db.models import BuilderBid as BuilderBidModel


class BuilderBidRepository:
    """Repository for builder_bids (Postgres)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_dict(self, row: BuilderBidModel) -> Dict[str, Any]:
        """Map SQLAlchemy row to API-friendly dict."""
        return {
            "id": row.id,
            "_id": row.id,
            "project_id": row.project_id,
            "builder_id": row.builder_id,
            "proposal_title": row.proposal_title,
            "proposal_details": row.proposal_details,
            "estimated_cost": row.estimated_cost,
            "estimated_duration": row.estimated_duration,
            "attachments": list(row.attachments) if row.attachments else [],
            "status": row.status,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    async def get_by_id(self, bid_id: str) -> Optional[Dict[str, Any]]:
        """Get builder bid by UUID."""
        result = await self.session.execute(
            select(BuilderBidModel).where(BuilderBidModel.id == bid_id)
        )
        row = result.scalar_one_or_none()
        return self._row_to_dict(row) if row else None

    async def list_by_project_id(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all bids for a project."""
        result = await self.session.execute(
            select(BuilderBidModel)
            .where(BuilderBidModel.project_id == project_id)
            .order_by(BuilderBidModel.created_at.desc())
        )
        rows = result.scalars().all()
        return [self._row_to_dict(r) for r in rows]

    async def list_by_builder_id(self, builder_id: str) -> List[Dict[str, Any]]:
        """Get all bids by a builder."""
        result = await self.session.execute(
            select(BuilderBidModel)
            .where(BuilderBidModel.builder_id == builder_id)
            .order_by(BuilderBidModel.created_at.desc())
        )
        rows = result.scalars().all()
        return [self._row_to_dict(r) for r in rows]

    async def get_by_project_and_builder(self, project_id: str, builder_id: str) -> Optional[Dict[str, Any]]:
        """Get a builder bid by project and builder."""
        result = await self.session.execute(
            select(BuilderBidModel)
            .where(
                BuilderBidModel.project_id == project_id,
                BuilderBidModel.builder_id == builder_id,
            )
        )
        row = result.scalar_one_or_none()
        return self._row_to_dict(row) if row else None

    async def create(self, data: Dict[str, Any]) -> BuilderBidModel:
        """Create a builder bid. Returns the row (with id set)."""
        row = BuilderBidModel(
            project_id=data["project_id"],
            builder_id=data["builder_id"],
            proposal_title=data["proposal_title"],
            proposal_details=data["proposal_details"],
            estimated_cost=data["estimated_cost"],
            estimated_duration=data["estimated_duration"],
            attachments=data.get("attachments") or [],
            status=data.get("status", "pending"),
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def update(self, bid_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update builder bid by id."""
        from datetime import datetime

        result = await self.session.execute(
            select(BuilderBidModel).where(BuilderBidModel.id == bid_id)
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

    async def delete(self, bid_id: str) -> bool:
        """Delete builder bid by id."""
        result = await self.session.execute(
            select(BuilderBidModel).where(BuilderBidModel.id == bid_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True


async def get_builder_bid_repository(
    session: AsyncSession = Depends(get_db_session),
) -> BuilderBidRepository:
    return BuilderBidRepository(session)
