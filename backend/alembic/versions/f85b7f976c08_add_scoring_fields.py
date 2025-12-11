"""add scoring fields

Revision ID: f85b7f976c08
Revises: e44df6ab5669
Create Date: 2025-12-11 05:50:09.246589

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f85b7f976c08"
down_revision: str | None = "e44df6ab5669"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add priority_score to authors
    op.add_column(
        "authors", sa.Column("priority_score", sa.Integer(), nullable=False, server_default="0")
    )

    # Add score fields to books
    op.add_column("books", sa.Column("investment_grade", sa.Integer(), nullable=True))
    op.add_column("books", sa.Column("strategic_fit", sa.Integer(), nullable=True))
    op.add_column("books", sa.Column("collection_impact", sa.Integer(), nullable=True))
    op.add_column("books", sa.Column("overall_score", sa.Integer(), nullable=True))
    op.add_column("books", sa.Column("scores_calculated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("books", "scores_calculated_at")
    op.drop_column("books", "overall_score")
    op.drop_column("books", "collection_impact")
    op.drop_column("books", "strategic_fit")
    op.drop_column("books", "investment_grade")
    op.drop_column("authors", "priority_score")
