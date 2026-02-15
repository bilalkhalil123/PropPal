"""Add last_checked to properties.

Revision ID: 002_add_last_checked
Revises: 001_initial
Create Date: 2026-02-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_add_last_checked"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "properties",
        sa.Column("last_checked", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("properties", "last_checked")
