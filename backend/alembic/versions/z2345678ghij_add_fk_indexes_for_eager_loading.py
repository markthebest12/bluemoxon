"""Add indexes on FK columns for eager loading optimization.

Revision ID: z2345678ghij
Revises: z1234567defg
Create Date: 2026-01-22

Issue #1239: SQLAlchemy eager loading uses correlated subqueries on
author_id, publisher_id, and binder_id. Without indexes, these cause
full table scans on the books table for each row in the entity list.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z2345678ghij"
down_revision: str | None = "z1234567defg"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add indexes on FK columns used by correlated subqueries.

    These indexes optimize the book_count subqueries in:
    - GET /authors (filters on Book.author_id)
    - GET /publishers (filters on Book.publisher_id)
    - GET /binders (filters on Book.binder_id)
    """
    op.create_index("books_author_id_idx", "books", ["author_id"])
    op.create_index("books_publisher_id_idx", "books", ["publisher_id"])
    op.create_index("books_binder_id_idx", "books", ["binder_id"])


def downgrade() -> None:
    """Remove FK indexes."""
    op.drop_index("books_binder_id_idx", "books")
    op.drop_index("books_publisher_id_idx", "books")
    op.drop_index("books_author_id_idx", "books")
