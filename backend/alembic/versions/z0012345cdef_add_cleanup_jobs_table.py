"""Add cleanup_jobs table for tracking async cleanup operations.

Revision ID: z0012345cdef
Revises: 5bd4bb0308b4
Create Date: 2026-01-11

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "z0012345cdef"
down_revision = "5bd4bb0308b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cleanup_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("deleted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cleanup_jobs_status",
        "cleanup_jobs",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_cleanup_jobs_status", table_name="cleanup_jobs")
    op.drop_table("cleanup_jobs")
