"""
Conversation repository (PostgreSQL/Neon).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Depends
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import get_db_session
from db.models import Conversation as ConversationModel
from db.models import ConversationMessage as ConversationMessageModel
from db.models import ConversationParticipant as ConversationParticipantModel


class ConversationRepository:
    """Repository for conversations (Postgres)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _normalize_participants(self, participant_ids: List[str]) -> Optional[Tuple[str, str]]:
        unique_ids = sorted({pid for pid in participant_ids if pid})
        if len(unique_ids) == 1:
            # Self-chat: same user on both sides (e.g. testing buyer+builder with one account)
            return unique_ids[0], unique_ids[0]
        if len(unique_ids) == 2:
            return unique_ids[0], unique_ids[1]
        return None

    async def find_existing(
        self,
        participant_ids: List[str],
        conversation_type: str,
        project_id: Optional[str] = None,
        bid_id: Optional[str] = None,
    ) -> Optional[ConversationModel]:
        """Find an existing conversation between two users.
        
        Only matches by participants — one conversation per pair of users,
        regardless of which project or bid initiated it.
        """
        pair = self._normalize_participants(participant_ids)
        if not pair:
            return None

        user_one_id, user_two_id = pair
        result = await self.session.execute(
            select(ConversationModel).where(
                ConversationModel.user_one_id == user_one_id,
                ConversationModel.user_two_id == user_two_id,
            ).order_by(ConversationModel.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        participant_ids: List[str],
        conversation_type: str,
        project_id: Optional[str] = None,
        bid_id: Optional[str] = None,
    ) -> ConversationModel:
        pair = self._normalize_participants(participant_ids)
        if not pair:
            raise ValueError("Exactly two participants are required for a conversation.")
        user_one_id, user_two_id = pair

        conversation = ConversationModel(
            conversation_type=conversation_type,
            user_one_id=user_one_id,
            user_two_id=user_two_id,
            project_id=project_id,
            bid_id=bid_id,
        )
        self.session.add(conversation)
        await self.session.flush()
        # Deduplicate so self-chat doesn't violate the composite PK
        unique_participant_ids = list(dict.fromkeys([user_one_id, user_two_id]))
        self.session.add_all(
            [
                ConversationParticipantModel(conversation_id=conversation.id, user_id=uid)
                for uid in unique_participant_ids
            ]
        )
        await self.session.flush()
        await self.session.refresh(conversation)
        return conversation

    async def add_message(
        self,
        conversation_id: str,
        sender_id: str,
        content: str,
    ) -> ConversationMessageModel:
        now = datetime.utcnow()
        message = ConversationMessageModel(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
            created_at=now,
        )
        self.session.add(message)
        await self.session.flush()
        await self.session.execute(
            update(ConversationModel)
            .where(ConversationModel.id == conversation_id)
            .values(updated_at=now)
        )
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def list_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        result = await self.session.execute(
            select(ConversationModel)
            .where(
                or_(
                    ConversationModel.user_one_id == user_id,
                    ConversationModel.user_two_id == user_id,
                )
            )
            .order_by(ConversationModel.updated_at.desc())
        )
        conversations = result.scalars().all()
        data: List[Dict[str, Any]] = []
        for convo in conversations:
            participant_ids = [convo.user_one_id, convo.user_two_id]
            last_message = await self.get_last_message(convo.id)
            data.append(
                {
                    "id": convo.id,
                    "_id": convo.id,
                    "conversation_type": convo.conversation_type,
                    "project_id": convo.project_id,
                    "bid_id": convo.bid_id,
                    "participant_ids": participant_ids,
                    "last_message": last_message.get("content") if last_message else None,
                    "last_message_at": last_message.get("created_at") if last_message else None,
                    "created_at": convo.created_at,
                    "updated_at": convo.updated_at,
                }
            )
        return data

    async def list_messages(self, conversation_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        result = await self.session.execute(
            select(ConversationMessageModel)
            .where(ConversationMessageModel.conversation_id == conversation_id)
            .order_by(ConversationMessageModel.created_at.asc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return [
            {
                "id": row.id,
                "_id": row.id,
                "conversation_id": row.conversation_id,
                "sender_id": row.sender_id,
                "content": row.content,
                "created_at": row.created_at,
            }
            for row in rows
        ]

    async def get_participant_ids(self, conversation_id: str) -> List[str]:
        result = await self.session.execute(
            select(ConversationModel).where(ConversationModel.id == conversation_id)
        )
        convo = result.scalar_one_or_none()
        if not convo:
            return []
        return [convo.user_one_id, convo.user_two_id]

    async def get_last_message(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        result = await self.session.execute(
            select(ConversationMessageModel)
            .where(ConversationMessageModel.conversation_id == conversation_id)
            .order_by(ConversationMessageModel.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return {
            "id": row.id,
            "_id": row.id,
            "conversation_id": row.conversation_id,
            "sender_id": row.sender_id,
            "content": row.content,
            "created_at": row.created_at,
        }


async def get_conversation_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ConversationRepository:
    return ConversationRepository(session)
