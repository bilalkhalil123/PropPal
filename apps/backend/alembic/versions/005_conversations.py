"""conversation tables for direct user chat

Revision ID: 005_conversations
Revises: 004_booking
Create Date: 2026-05-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "005_conversations"
down_revision: Union[str, None] = "004_booking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("conversation_type", sa.String(length=50), nullable=False),
        sa.Column("user_one_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_two_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("bid_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_one_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_two_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["user_projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["bid_id"], ["builder_bids.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_user_one_id", "conversations", ["user_one_id"], unique=False)
    op.create_index("ix_conversations_user_two_id", "conversations", ["user_two_id"], unique=False)
    op.create_index("ix_conversations_user_pair", "conversations", ["user_one_id", "user_two_id"], unique=False)
    op.create_index("ix_conversations_project_id", "conversations", ["project_id"], unique=False)
    op.create_index("ix_conversations_bid_id", "conversations", ["bid_id"], unique=False)

    op.create_table(
        "conversation_messages",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversation_messages_conversation_created",
        "conversation_messages",
        ["conversation_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_messages_conversation_created", table_name="conversation_messages")
    op.drop_table("conversation_messages")
    op.drop_index("ix_conversations_user_pair", table_name="conversations")
    op.drop_index("ix_conversations_user_two_id", table_name="conversations")
    op.drop_index("ix_conversations_user_one_id", table_name="conversations")
    op.drop_index("ix_conversations_bid_id", table_name="conversations")
    op.drop_index("ix_conversations_project_id", table_name="conversations")
    op.drop_table("conversations")
