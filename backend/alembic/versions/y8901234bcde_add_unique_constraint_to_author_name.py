"""add_unique_constraint_to_author_name

Add unique constraint to author name column to prevent duplicate authors.

Revision ID: y8901234bcde
Revises: x7890123abcd
Create Date: 2026-01-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "y8901234bcde"
down_revision: str | None = "x7890123abcd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add unique constraint to authors.name."""
    op.create_unique_constraint("uq_authors_name", "authors", ["name"])


def downgrade() -> None:
    """Remove unique constraint from authors.name."""
    op.drop_constraint("uq_authors_name", "authors", type_="unique")
