"""Add ai_connections column to entity_profiles.

Revision ID: e9a5101c8557
Revises: z4567890klmn
Create Date: 2026-02-05

Issue #1804: Store AI-discovered personal connections (family,
friendship, influence, collaboration, scandal) as JSON.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e9a5101c8557"
down_revision: str | None = "z4567890klmn"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ai_connections JSONB column."""
    op.add_column("entity_profiles", sa.Column("ai_connections", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Drop ai_connections column."""
    op.drop_column("entity_profiles", "ai_connections")
