"""add_model_id_to_analyses

Add model_id column to book_analyses table for tracking which AI model
generated each analysis.

Revision ID: 5d2aef44594e
Revises: v5678901uvwx
Create Date: 2025-12-31 00:00:20.812404

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d2aef44594e"
down_revision: str | None = "v5678901uvwx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add model_id column to book_analyses table."""
    op.add_column(
        "book_analyses",
        sa.Column("model_id", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    """Remove model_id column from book_analyses table."""
    op.drop_column("book_analyses", "model_id")
