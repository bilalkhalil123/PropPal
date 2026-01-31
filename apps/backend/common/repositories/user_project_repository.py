"""
User project repository (PostgreSQL/Neon). IDs are UUID strings.
"""

from typing import Any, Dict, List, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import get_db_session
from db.models import UserProject as UserProjectModel


class UserProjectRepository:
    """Repository for user_projects (Postgres)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_dict(self, row: UserProjectModel) -> Dict[str, Any]:
        """Map SQLAlchemy row to API-friendly dict."""
        return {
            "id": row.id,
            "_id": row.id,
            "user_id": row.user_id,
            "property_id": row.property_id,
            "title": row.title,
            "description": row.description,
            "project_type": row.project_type,
            "budget_min": row.budget_min,
            "budget_max": row.budget_max,
            "location": row.location,
            "status": row.status,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    async def get_by_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get user project by UUID."""
        result = await self.session.execute(
            select(UserProjectModel).where(UserProjectModel.id == project_id)
        )
        row = result.scalar_one_or_none()
        return self._row_to_dict(row) if row else None

    async def list_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all projects for a user."""
        result = await self.session.execute(
            select(UserProjectModel)
            .where(UserProjectModel.user_id == user_id)
            .order_by(UserProjectModel.created_at.desc())
        )
        rows = result.scalars().all()
        return [self._row_to_dict(r) for r in rows]

    async def create(self, data: Dict[str, Any]) -> UserProjectModel:
        """Create a user project. Returns the row (with id set)."""
        row = UserProjectModel(
            user_id=data["user_id"],
            property_id=data.get("property_id"),
            title=data["title"],
            description=data["description"],
            project_type=data["project_type"],
            budget_min=data["budget_min"],
            budget_max=data["budget_max"],
            location=data["location"],
            status=data.get("status", "open"),
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def update(self, project_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user project by id."""
        from datetime import datetime

        result = await self.session.execute(
            select(UserProjectModel).where(UserProjectModel.id == project_id)
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

    async def delete(self, project_id: str) -> bool:
        """Delete user project by id."""
        result = await self.session.execute(
            select(UserProjectModel).where(UserProjectModel.id == project_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True


async def get_user_project_repository(
    session: AsyncSession = Depends(get_db_session),
) -> UserProjectRepository:
    return UserProjectRepository(session)
