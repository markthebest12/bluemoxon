"""add image processing indexes and fix failure_reason type

Revision ID: 0fc4653fe40b
Revises: d4e5f6g7h8i9
Create Date: 2026-01-16 16:28:35.664492

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0fc4653fe40b"
down_revision: str | None = "d4e5f6g7h8i9"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Change failure_reason from VARCHAR(500) to TEXT
    op.alter_column(
        "image_processing_jobs",
        "failure_reason",
        existing_type=sa.String(500),
        type_=sa.Text(),
        existing_nullable=True,
    )

    # Create composite index for query optimization
    # Using raw SQL for CONCURRENTLY to avoid locking in production
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "ix_image_processing_jobs_query "
        "ON image_processing_jobs (book_id, source_image_id, status)"
    )

    # Create unique partial index to prevent duplicate pending/processing jobs
    op.execute(
        "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS "
        "ix_image_processing_jobs_pending_unique "
        "ON image_processing_jobs (book_id, source_image_id) "
        "WHERE status IN ('pending', 'processing')"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_image_processing_jobs_pending_unique")
    op.execute("DROP INDEX IF EXISTS ix_image_processing_jobs_query")

    op.alter_column(
        "image_processing_jobs",
        "failure_reason",
        existing_type=sa.Text(),
        type_=sa.String(500),
        existing_nullable=True,
    )
