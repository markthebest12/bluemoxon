"""Add failed_count column to cleanup_jobs table.

Revision ID: a1f2e3d4c5b6
Revises: z0012345cdef
Create Date: 2026-01-11

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1f2e3d4c5b6"
down_revision = "z0012345cdef"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cleanup_jobs",
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("cleanup_jobs", "failed_count")
