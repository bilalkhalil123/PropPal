"""
Conversation API for direct user-to-user messaging.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from common.repositories.conversation_repository import (
    ConversationRepository,
    get_conversation_repository,
)
from common.repositories.user_repository import UserRepository, get_user_repository
from common.repositories.builder_profile_repository import (
    BuilderProfileRepository,
    get_builder_profile_repository,
)
from models.conversations import (
    ConversationCreate,
    ConversationMessageCreate,
    ConversationMessageResponse,
    ConversationResponse,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


async def _resolve_user_id(
    clerk_id: Optional[str],
    user_repo: UserRepository,
) -> str:
    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="clerk_id is required",
        )
    user = await user_repo.get_user_by_clerk_id(clerk_id)
    if not user or not getattr(user, "id", None):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with clerk_id {clerk_id} not found",
        )
    return str(user.id)


@router.get("", response_model=dict)
async def list_conversations(
    clerk_id: Optional[str] = Query(None),
    user_repo: UserRepository = Depends(get_user_repository),
    repo: ConversationRepository = Depends(get_conversation_repository),
    builder_repo: BuilderProfileRepository = Depends(get_builder_profile_repository),
):
    user_id = await _resolve_user_id(clerk_id, user_repo)
    conversations = await repo.list_for_user(user_id)

    # Collect all unique participant IDs across conversations
    all_participant_ids: list[str] = []
    for convo in conversations:
        for pid in convo.get("participant_ids", []):
            if pid and pid not in all_participant_ids:
                all_participant_ids.append(pid)

    # Batch-fetch all users in ONE query
    users = await user_repo.get_users_by_ids(all_participant_ids)
    user_name_map: dict[str, str] = {}
    user_role_map: dict[str, str] = {}
    builder_user_ids: list[str] = []
    for u in users:
        user_name_map[u.id] = u.name or "Unknown"
        user_role_map[u.id] = u.role or "buyer"
        if u.role == "builder":
            builder_user_ids.append(u.id)

    # Batch-fetch all builder profiles in ONE query
    builder_company_map: dict[str, str] = {}
    if builder_user_ids:
        profiles = await builder_repo.list_by_user_ids(builder_user_ids)
        for p in profiles:
            builder_company_map[p["user_id"]] = p.get("company_name", "")

    # Enrich each conversation with participant info
    for convo in conversations:
        pids = convo.get("participant_ids", [])
        convo["participant_names"] = {
            pid: user_name_map.get(pid, "Unknown") for pid in pids if pid
        }
        convo["participant_roles"] = {
            pid: user_role_map.get(pid, "buyer") for pid in pids if pid
        }
        convo["builder_companies"] = {
            pid: builder_company_map[pid] for pid in pids if pid in builder_company_map
        }
        # Determine the "other" participant for easy display
        other_id = next((pid for pid in pids if pid != user_id), pids[0] if pids else None)
        if other_id:
            convo["other_participant"] = {
                "id": other_id,
                "name": user_name_map.get(other_id, "Unknown"),
                "role": user_role_map.get(other_id, "buyer"),
                "company_name": builder_company_map.get(other_id),
            }

    return {"conversations": conversations}


@router.post("", response_model=dict)
async def start_conversation(
    payload: ConversationCreate,
    clerk_id: Optional[str] = Query(None),
    user_repo: UserRepository = Depends(get_user_repository),
    repo: ConversationRepository = Depends(get_conversation_repository),
):
    user_id = await _resolve_user_id(clerk_id, user_repo)
    # Include current user + payload participants; pass all (including duplicates) to repo
    participant_ids = list(payload.participant_ids) + [user_id]

    existing = await repo.find_existing(
        participant_ids=participant_ids,
        conversation_type=payload.conversation_type,
        project_id=payload.project_id,
        bid_id=payload.bid_id,
    )
    conversation = existing
    if not conversation:
        conversation = await repo.create(
            participant_ids=participant_ids,
            conversation_type=payload.conversation_type,
            project_id=payload.project_id,
            bid_id=payload.bid_id,
        )

    if payload.initial_message:
        await repo.add_message(conversation.id, user_id, payload.initial_message)

    response = ConversationResponse(
        _id=conversation.id,
        conversation_type=conversation.conversation_type,
        project_id=conversation.project_id,
        bid_id=conversation.bid_id,
        participant_ids=participant_ids,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )
    return {"conversation": response.model_dump(by_alias=True)}


@router.get("/{conversation_id}/messages", response_model=dict)
async def list_messages(
    conversation_id: str,
    clerk_id: Optional[str] = Query(None),
    user_repo: UserRepository = Depends(get_user_repository),
    repo: ConversationRepository = Depends(get_conversation_repository),
    limit: int = Query(100, ge=1, le=200),
):
    user_id = await _resolve_user_id(clerk_id, user_repo)
    participants = await repo.get_participant_ids(conversation_id)
    if not participants:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if user_id not in participants:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant")
    messages = await repo.list_messages(conversation_id, limit=limit)
    return {"messages": messages}


@router.post("/{conversation_id}/messages", response_model=dict)
async def send_message(
    conversation_id: str,
    payload: ConversationMessageCreate,
    clerk_id: Optional[str] = Query(None),
    user_repo: UserRepository = Depends(get_user_repository),
    repo: ConversationRepository = Depends(get_conversation_repository),
):
    user_id = await _resolve_user_id(clerk_id, user_repo)
    participants = await repo.get_participant_ids(conversation_id)
    if not participants:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if user_id not in participants:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant")
    message = await repo.add_message(conversation_id, user_id, payload.content)
    response = ConversationMessageResponse(
        _id=message.id,
        conversation_id=message.conversation_id,
        sender_id=message.sender_id,
        content=message.content,
        created_at=message.created_at,
    )
    return {"message": response.model_dump(by_alias=True)}
