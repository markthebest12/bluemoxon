"""Add image_url to entity tables (authors, publishers, binders).

Revision ID: z3456789ijkl
Revises: z2345678ghij
Create Date: 2026-02-02

Issue #1632: Add image_url column to entity tables for portrait images.
Stores the CloudFront CDN URL for admin-uploaded entity portraits.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z3456789ijkl"
down_revision: str | None = "z2345678ghij"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add image_url column to authors, publishers, and binders tables."""
    op.add_column("authors", sa.Column("image_url", sa.String(500), nullable=True))
    op.add_column("publishers", sa.Column("image_url", sa.String(500), nullable=True))
    op.add_column("binders", sa.Column("image_url", sa.String(500), nullable=True))


def downgrade() -> None:
    """Remove image_url column from entity tables."""
    op.drop_column("binders", "image_url")
    op.drop_column("publishers", "image_url")
    op.drop_column("authors", "image_url")
