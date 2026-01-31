"""Initial schema: users, properties, builder_profiles, builder_services, user_projects, builder_bids, chat_histories, availability, visits.

Revision ID: 001_initial
Revises:
Create Date: 2025-01-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("profile_image", sa.Text(), nullable=True),
        sa.Column("clerk_id", sa.String(255), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_clerk_id", "users", ["clerk_id"], unique=True)
    op.create_index("ix_users_role", "users", ["role"], unique=False)

    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("seller_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("property_type", sa.String(100), nullable=False),
        sa.Column("area_sqft", sa.Float(), nullable=False),
        sa.Column("bedrooms", sa.Integer(), nullable=False),
        sa.Column("bathrooms", sa.Integer(), nullable=False),
        sa.Column("floors", sa.Integer(), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("area", sa.String(100), nullable=False),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("images", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("date_added", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_properties_seller_id", "properties", ["seller_id"], unique=False)
    op.create_index("ix_properties_city", "properties", ["city"], unique=False)
    op.create_index("ix_properties_property_type", "properties", ["property_type"], unique=False)
    op.create_index("ix_properties_bedrooms", "properties", ["bedrooms"], unique=False)
    op.create_index("ix_properties_price", "properties", ["price"], unique=False)
    op.create_index("ix_properties_created_at", "properties", ["created_at"], unique=False)

    op.create_table(
        "builder_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("specialization", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("experience_years", sa.Integer(), nullable=False),
        sa.Column("portfolio_images", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("about", sa.Text(), nullable=True),
        sa.Column("founded_year", sa.Integer(), nullable=True),
        sa.Column("location", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_builder_profiles_user_id", "builder_profiles", ["user_id"], unique=True)

    op.create_table(
        "builder_services",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("builder_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("base_price", sa.Float(), nullable=False),
        sa.Column("price_unit", sa.String(50), nullable=False),
        sa.Column("estimated_duration", sa.String(100), nullable=True),
        sa.Column("service_features", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("service_images", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["builder_id"], ["builder_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_builder_services_builder_id", "builder_services", ["builder_id"], unique=False)
    op.create_index("ix_builder_services_category", "builder_services", ["category"], unique=False)

    op.create_table(
        "user_projects",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("project_type", sa.String(100), nullable=False),
        sa.Column("budget_min", sa.Float(), nullable=False),
        sa.Column("budget_max", sa.Float(), nullable=False),
        sa.Column("location", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_projects_user_id", "user_projects", ["user_id"], unique=False)
    op.create_index("ix_user_projects_property_id", "user_projects", ["property_id"], unique=False)

    op.create_table(
        "builder_bids",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("builder_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("proposal_title", sa.String(200), nullable=False),
        sa.Column("proposal_details", sa.Text(), nullable=False),
        sa.Column("estimated_cost", sa.Float(), nullable=False),
        sa.Column("estimated_duration", sa.String(100), nullable=False),
        sa.Column("attachments", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["user_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["builder_id"], ["builder_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_builder_bids_project_id", "builder_bids", ["project_id"], unique=False)
    op.create_index("ix_builder_bids_builder_id", "builder_bids", ["builder_id"], unique=False)

    op.create_table(
        "chat_histories",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("messages", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_histories_user_id", "chat_histories", ["user_id"], unique=False)
    op.create_index("ix_chat_histories_session_id", "chat_histories", ["session_id"], unique=False)

    op.create_table(
        "availability",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("seller_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("slots", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_availability_property_id", "availability", ["property_id"], unique=False)
    op.create_index("ix_availability_seller_id", "availability", ["seller_id"], unique=False)

    op.create_table(
        "visits",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("buyer_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("builder_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("proposed_time_slots", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("confirmed_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("agent_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["builder_id"], ["builder_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_visits_buyer_id", "visits", ["buyer_id"], unique=False)
    op.create_index("ix_visits_property_id", "visits", ["property_id"], unique=False)
    op.create_index("ix_visits_builder_id", "visits", ["builder_id"], unique=False)


def downgrade() -> None:
    op.drop_table("visits")
    op.drop_table("availability")
    op.drop_table("chat_histories")
    op.drop_table("builder_bids")
    op.drop_table("user_projects")
    op.drop_table("builder_services")
    op.drop_table("builder_profiles")
    op.drop_table("properties")
    op.drop_table("users")
