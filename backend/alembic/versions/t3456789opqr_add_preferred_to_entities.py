"""add_preferred_to_entities

Add preferred boolean field to authors, publishers, and binders tables.

Revision ID: t3456789opqr
Revises: f4f2fbe81faa
Create Date: 2025-12-29 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "t3456789opqr"
down_revision: str | None = "f4f2fbe81faa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add preferred column to entity tables."""
    op.add_column(
        "authors",
        sa.Column("preferred", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "publishers",
        sa.Column("preferred", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "binders",
        sa.Column("preferred", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    """Remove preferred column from entity tables."""
    op.drop_column("binders", "preferred")
    op.drop_column("publishers", "preferred")
    op.drop_column("authors", "preferred")
