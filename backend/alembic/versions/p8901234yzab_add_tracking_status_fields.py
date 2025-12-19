"""Add tracking_status and tracking_last_checked to books.

Revision ID: p8901234yzab
Revises: o7890123wxyz
Create Date: 2025-12-18
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "p8901234yzab"
down_revision = "o7890123wxyz"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "books",
        sa.Column("tracking_status", sa.String(100), nullable=True)
    )
    op.add_column(
        "books",
        sa.Column("tracking_last_checked", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("books", "tracking_last_checked")
    op.drop_column("books", "tracking_status")
