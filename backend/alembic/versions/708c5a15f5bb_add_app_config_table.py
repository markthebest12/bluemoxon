"""Add app_config table for runtime key-value configuration.

Revision ID: 708c5a15f5bb
Revises: f7624c3b4e76
Create Date: 2026-02-03

Issue #1571: Add app_config table to store runtime configuration
such as model selections per workflow.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "708c5a15f5bb"
down_revision: str | None = "f7624c3b4e76"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create app_config table."""
    op.create_table(
        "app_config",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.String(500), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column("updated_by", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    """Drop app_config table."""
    op.drop_table("app_config")
