"""
User repository for database operations (PostgreSQL/Neon).

Uses async SQLAlchemy session; IDs are UUID strings.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import get_db_session
from db.models import User as UserModel
from models.users import User


class UserRepository:
    """Repository for user database operations (Postgres)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_user(self, row: UserModel) -> User:
        """Map SQLAlchemy User row to Pydantic User (id as string)."""
        return User(
            _id=row.id,
            name=row.name,
            email=row.email,
            phone=row.phone,
            role=row.role,
            profile_image=row.profile_image,
            clerk_id=row.clerk_id,
            password_hash=row.password_hash,
            deleted_at=row.deleted_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """Create a new user in the database."""
        now = datetime.utcnow()
        user_data.setdefault("created_at", now)
        user_data.setdefault("updated_at", now)
        row = UserModel(
            name=user_data["name"],
            email=user_data["email"],
            phone=user_data.get("phone"),
            role=user_data["role"],
            profile_image=user_data.get("profile_image"),
            clerk_id=user_data.get("clerk_id"),
            password_hash=user_data.get("password_hash"),
            deleted_at=user_data.get("deleted_at"),
            created_at=user_data["created_at"],
            updated_at=user_data["updated_at"],
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return self._row_to_user(row)

    async def get_user_by_clerk_id(self, clerk_id: str) -> Optional[User]:
        """Get user by Clerk ID."""
        result = await self.session.execute(
            select(UserModel).where(
                UserModel.clerk_id == clerk_id,
                UserModel.deleted_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        return self._row_to_user(row) if row else None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by UUID string."""
        result = await self.session.execute(
            select(UserModel).where(
                UserModel.id == user_id,
                UserModel.deleted_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        return self._row_to_user(row) if row else None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.session.execute(
            select(UserModel).where(
                UserModel.email == email,
                UserModel.deleted_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        return self._row_to_user(row) if row else None

    async def update_user(self, clerk_id: str, update_data: Dict[str, Any]) -> Optional[User]:
        """Update user data."""
        update_data["updated_at"] = datetime.utcnow()
        result = await self.session.execute(
            select(UserModel).where(UserModel.clerk_id == clerk_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        for k, v in update_data.items():
            if hasattr(row, k):
                setattr(row, k, v)
        await self.session.flush()
        await self.session.refresh(row)
        return self._row_to_user(row)

    async def soft_delete_user(self, clerk_id: str) -> bool:
        """Soft delete user (mark as deleted)."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.clerk_id == clerk_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        row.deleted_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        await self.session.flush()
        return True

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination."""
        result = await self.session.execute(
            select(UserModel)
            .where(UserModel.deleted_at.is_(None))
            .offset(skip)
            .limit(limit)
        )
        rows = result.scalars().all()
        return [self._row_to_user(r) for r in rows]

    async def get_users_by_role(self, role: str, skip: int = 0, limit: int = 100) -> List[User]:
        """Get users by role."""
        result = await self.session.execute(
            select(UserModel)
            .where(UserModel.role == role, UserModel.deleted_at.is_(None))
            .offset(skip)
            .limit(limit)
        )
        rows = result.scalars().all()
        return [self._row_to_user(r) for r in rows]

    async def user_exists(self, clerk_id: str) -> bool:
        """Check if user exists by Clerk ID."""
        result = await self.session.execute(
            select(UserModel.id).where(UserModel.clerk_id == clerk_id)
        )
        return result.scalar_one_or_none() is not None

    async def get_users_by_ids(self, user_ids: List[str]) -> List[User]:
        """Batch fetch users by a list of UUID strings (single query)."""
        if not user_ids:
            return []
        result = await self.session.execute(
            select(UserModel).where(
                UserModel.id.in_(user_ids),
                UserModel.deleted_at.is_(None),
            )
        )
        rows = result.scalars().all()
        return [self._row_to_user(r) for r in rows]

    # Aliases for plan: same method names (get_by_id, get_by_email, get_by_clerk_id, create)
    async def get_by_id(self, user_id: str) -> Optional[User]:
        return await self.get_user_by_id(user_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        return await self.get_user_by_email(email)

    async def get_by_clerk_id(self, clerk_id: str) -> Optional[User]:
        return await self.get_user_by_clerk_id(clerk_id)

    async def create(self, user_data: Dict[str, Any]) -> User:
        return await self.create_user(user_data)

    async def get_user_stats(self) -> Dict[str, int]:
        """Get user statistics."""
        from sqlalchemy import func

        total = (await self.session.execute(select(func.count()).select_from(UserModel).where(UserModel.deleted_at.is_(None)))).scalar() or 0
        buyers = (await self.session.execute(select(func.count()).select_from(UserModel).where(UserModel.role == "buyer", UserModel.deleted_at.is_(None)))).scalar() or 0
        sellers = (await self.session.execute(select(func.count()).select_from(UserModel).where(UserModel.role == "seller", UserModel.deleted_at.is_(None)))).scalar() or 0
        builders = (await self.session.execute(select(func.count()).select_from(UserModel).where(UserModel.role == "builder", UserModel.deleted_at.is_(None)))).scalar() or 0
        admins = (await self.session.execute(select(func.count()).select_from(UserModel).where(UserModel.role == "admin", UserModel.deleted_at.is_(None)))).scalar() or 0
        return {
            "total_users": total,
            "buyers": buyers,
            "sellers": sellers,
            "builders": builders,
            "admins": admins,
        }


async def get_user_repository(session: AsyncSession = Depends(get_db_session)) -> UserRepository:
    """Get user repository instance (Postgres session)."""
    return UserRepository(session)
