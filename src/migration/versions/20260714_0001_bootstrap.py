"""bootstrap vacancy dictionaries schema

Revision ID: 20260714_0001
Revises:
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from models.dictionaries import Base

revision: str = "20260714_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())
    for table in Base.metadata.sorted_tables:
        if "name" in table.c:
            op.create_index(f"ix_{table.name}_name_ci", table.name, [sa.text("lower(name)")])


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
