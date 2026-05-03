"""
Builder profile repository (PostgreSQL/Neon). IDs are UUID strings.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import get_db_session
from db.models import BuilderProfile as BuilderProfileModel


class BuilderProfileRepository:
    """Repository for builder_profiles (Postgres)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_dict(self, row: BuilderProfileModel) -> Dict[str, Any]:
        """Map SQLAlchemy row to API-friendly dict (id, user_id as string)."""
        return {
            "id": row.id,
            "_id": row.id,
            "user_id": row.user_id,
            "company_name": row.company_name,
            "specialization": list(row.specialization) if row.specialization else [],
            "experience_years": row.experience_years,
            "portfolio_images": list(row.portfolio_images) if row.portfolio_images else [],
            "rating": row.rating,
            "about": row.about,
            "founded_year": row.founded_year,
            "location": row.location,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    async def get_by_id(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get builder profile by UUID."""
        result = await self.session.execute(
            select(BuilderProfileModel).where(BuilderProfileModel.id == profile_id)
        )
        row = result.scalar_one_or_none()
        return self._row_to_dict(row) if row else None

    async def get_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get builder profile by user UUID."""
        result = await self.session.execute(
            select(BuilderProfileModel).where(BuilderProfileModel.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        return self._row_to_dict(row) if row else None

    async def create(self, data: Dict[str, Any]) -> BuilderProfileModel:
        """Create a builder profile. Returns the row (with id set)."""
        row = BuilderProfileModel(
            user_id=data["user_id"],
            company_name=data["company_name"],
            specialization=data.get("specialization") or [],
            experience_years=data["experience_years"],
            portfolio_images=data.get("portfolio_images"),
            rating=data.get("rating"),
            about=data.get("about"),
            founded_year=data.get("founded_year"),
            location=data.get("location"),
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def update(self, profile_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update builder profile by id."""
        result = await self.session.execute(
            select(BuilderProfileModel).where(BuilderProfileModel.id == profile_id)
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

    async def delete(self, profile_id: str) -> bool:
        """Delete builder profile by id."""
        result = await self.session.execute(
            select(BuilderProfileModel).where(BuilderProfileModel.id == profile_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True

    async def list_by_ids(self, profile_ids: List[str]) -> List[Dict[str, Any]]:
        """Get multiple profiles by UUIDs (for search results)."""
        if not profile_ids:
            return []
        result = await self.session.execute(
            select(BuilderProfileModel).where(BuilderProfileModel.id.in_(profile_ids))
        )
        rows = result.scalars().all()
        return [self._row_to_dict(r) for r in rows]

    async def list_by_user_ids(self, user_ids: List[str]) -> List[Dict[str, Any]]:
        """Get builder profiles by a list of user UUIDs (single query)."""
        if not user_ids:
            return []
        result = await self.session.execute(
            select(BuilderProfileModel).where(BuilderProfileModel.user_id.in_(user_ids))
        )
        rows = result.scalars().all()
        return [self._row_to_dict(r) for r in rows]

    async def list_all(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """List all builder profiles with pagination."""
        result = await self.session.execute(
            select(BuilderProfileModel)
            .order_by(BuilderProfileModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        rows = result.scalars().all()
        return [self._row_to_dict(r) for r in rows]


async def get_builder_profile_repository(
    session: AsyncSession = Depends(get_db_session),
) -> BuilderProfileRepository:
    return BuilderProfileRepository(session)
