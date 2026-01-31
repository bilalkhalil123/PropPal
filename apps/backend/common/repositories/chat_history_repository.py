"""
Chat history repository (PostgreSQL/Neon). IDs are UUID strings.
"""

from typing import Any, Dict, List, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import get_db_session
from db.models import ChatHistory as ChatHistoryModel


class ChatHistoryRepository:
    """Repository for chat_histories (Postgres)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_dict(self, row: ChatHistoryModel) -> Dict[str, Any]:
        """Map SQLAlchemy row to API-friendly dict."""
        return {
            "id": row.id,
            "_id": row.id,
            "user_id": row.user_id,
            "session_id": row.session_id,
            "messages": row.messages if isinstance(row.messages, list) else (row.messages or []),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    async def get_by_id(self, history_id: str) -> Optional[Dict[str, Any]]:
        """Get chat history by UUID."""
        result = await self.session.execute(
            select(ChatHistoryModel).where(ChatHistoryModel.id == history_id)
        )
        row = result.scalar_one_or_none()
        return self._row_to_dict(row) if row else None

    async def get_by_user_and_session(
        self, user_id: str, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get chat history by user_id and session_id."""
        result = await self.session.execute(
            select(ChatHistoryModel).where(
                ChatHistoryModel.user_id == user_id,
                ChatHistoryModel.session_id == session_id,
            )
        )
        row = result.scalar_one_or_none()
        return self._row_to_dict(row) if row else None

    async def list_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all chat histories for a user (any session)."""
        result = await self.session.execute(
            select(ChatHistoryModel)
            .where(ChatHistoryModel.user_id == user_id)
            .order_by(ChatHistoryModel.updated_at.desc())
        )
        rows = result.scalars().all()
        return [self._row_to_dict(r) for r in rows]

    async def get_latest_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recently updated chat history for a user."""
        result = await self.session.execute(
            select(ChatHistoryModel)
            .where(ChatHistoryModel.user_id == user_id)
            .order_by(ChatHistoryModel.updated_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return self._row_to_dict(row) if row else None

    async def create(self, data: Dict[str, Any]) -> ChatHistoryModel:
        """Create a chat history. Returns the row (with id set)."""
        row = ChatHistoryModel(
            user_id=data["user_id"],
            session_id=data.get("session_id"),
            messages=data.get("messages") or [],
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def update_messages(
        self, user_id: str, session_id: str, messages: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Update messages for a user/session. Creates if not exists."""
        from datetime import datetime

        result = await self.session.execute(
            select(ChatHistoryModel).where(
                ChatHistoryModel.user_id == user_id,
                ChatHistoryModel.session_id == session_id,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            row.messages = messages
            row.updated_at = datetime.utcnow()
            await self.session.flush()
            await self.session.refresh(row)
            return self._row_to_dict(row)
        return None

    async def upsert_messages(
        self, user_id: str, session_id: str, messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create or update chat history with messages."""
        from datetime import datetime

        result = await self.session.execute(
            select(ChatHistoryModel).where(
                ChatHistoryModel.user_id == user_id,
                ChatHistoryModel.session_id == session_id,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            row.messages = messages
            row.updated_at = datetime.utcnow()
            await self.session.flush()
            await self.session.refresh(row)
            return self._row_to_dict(row)
        row = ChatHistoryModel(
            user_id=user_id,
            session_id=session_id,
            messages=messages,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return self._row_to_dict(row)

    async def delete_by_user_and_session(self, user_id: str, session_id: str) -> bool:
        """Delete chat history by user_id and session_id."""
        result = await self.session.execute(
            select(ChatHistoryModel).where(
                ChatHistoryModel.user_id == user_id,
                ChatHistoryModel.session_id == session_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True


async def get_chat_history_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ChatHistoryRepository:
    return ChatHistoryRepository(session)
