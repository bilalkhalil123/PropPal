"""Add nearby_amenities and amenity_summary columns to properties.

Revision ID: 003_add_amenity_cols
Revises: 002_add_last_checked
Create Date: 2026-03-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "003_add_amenity_cols"
down_revision: Union[str, None] = "002_add_last_checked"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("properties", sa.Column("nearby_amenities", JSONB, nullable=True))
    op.add_column("properties", sa.Column("amenity_summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("properties", "amenity_summary")
    op.drop_column("properties", "nearby_amenities")
