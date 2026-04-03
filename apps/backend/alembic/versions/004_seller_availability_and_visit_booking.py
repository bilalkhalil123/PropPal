"""seller_availability table and visit booking columns

Revision ID: 004_booking
Revises: a6ed59557d15
Create Date: 2026-04-03

day_of_week: 0=Monday .. 6=Sunday (Python datetime.weekday()).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004_booking"
down_revision: Union[str, None] = "a6ed59557d15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "seller_availability",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("seller_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("day_of_week", sa.SmallInteger(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_seller_availability_seller_property_dow",
        "seller_availability",
        ["seller_id", "property_id", "day_of_week"],
        unique=False,
    )
    op.create_index(
        "ix_seller_availability_property_id",
        "seller_availability",
        ["property_id"],
        unique=False,
    )

    op.add_column(
        "visits",
        sa.Column("seller_id", postgresql.UUID(as_uuid=False), nullable=True),
    )
    op.add_column(
        "visits",
        sa.Column("cancelled_by", postgresql.UUID(as_uuid=False), nullable=True),
    )
    op.add_column("visits", sa.Column("cancellation_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_visits_seller_id_users",
        "visits",
        "users",
        ["seller_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_visits_cancelled_by_users",
        "visits",
        "users",
        ["cancelled_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_visits_seller_id", "visits", ["seller_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_visits_seller_id", table_name="visits")
    op.drop_constraint("fk_visits_cancelled_by_users", "visits", type_="foreignkey")
    op.drop_constraint("fk_visits_seller_id_users", "visits", type_="foreignkey")
    op.drop_column("visits", "cancellation_reason")
    op.drop_column("visits", "cancelled_by")
    op.drop_column("visits", "seller_id")

    op.drop_index("ix_seller_availability_property_id", table_name="seller_availability")
    op.drop_index("ix_seller_availability_seller_property_dow", table_name="seller_availability")
    op.drop_table("seller_availability")
