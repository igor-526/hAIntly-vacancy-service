"""add filter_presets and filter_preset_values tables

Revision ID: 20260714_0002
Revises: 20260714_0001
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260714_0002"
down_revision: str | None = "20260714_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "filter_presets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("hh_user_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(63), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("excluded_text", sa.Text(), nullable=True),
        sa.Column("salary", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("salary_mode", sa.String(50), nullable=True),
        sa.Column("period", sa.Integer(), nullable=True),
        sa.Column("date_from", sa.String(30), nullable=True),
        sa.Column("date_to", sa.String(30), nullable=True),
        sa.Column("order_by", sa.String(50), nullable=True),
        sa.Column("premium", sa.Boolean(), nullable=True),
        sa.Column("accept_temporary", sa.Boolean(), nullable=True),
        sa.Column("no_magic", sa.Boolean(), nullable=True),
        sa.Column("top_lat", sa.Float(), nullable=True),
        sa.Column("bottom_lat", sa.Float(), nullable=True),
        sa.Column("left_lng", sa.Float(), nullable=True),
        sa.Column("right_lng", sa.Float(), nullable=True),
        sa.Column("sort_point_lat", sa.Float(), nullable=True),
        sa.Column("sort_point_lng", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("active", sa.Boolean(), server_default="true"),
        sa.UniqueConstraint("hh_user_id", "name", name="uq_filter_presets_hh_user_id_name"),
    )
    op.create_index("ix_filter_presets_hh_user_id", "filter_presets", ["hh_user_id"])
    op.create_index("ix_filter_presets_active", "filter_presets", ["active"])

    op.create_table(
        "filter_preset_values",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("preset_id", sa.Uuid(), sa.ForeignKey("filter_presets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parameter_name", sa.String(100), nullable=False),
        sa.Column("value", sa.String(200), nullable=False),
        sa.UniqueConstraint("preset_id", "parameter_name", "value", name="uq_filter_preset_values_pnv"),
    )
    op.create_index("ix_filter_preset_values_preset_id", "filter_preset_values", ["preset_id"])


def downgrade() -> None:
    op.drop_table("filter_preset_values")
    op.drop_table("filter_presets")
