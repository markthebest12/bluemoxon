"""add image processing indexes and fix failure_reason type

Revision ID: 0fc4653fe40b
Revises: d4e5f6g7h8i9
Create Date: 2026-01-16 16:28:35.664492

Note: This migration uses CREATE INDEX CONCURRENTLY which cannot run inside
a transaction. We use autocommit mode for the index operations.
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
    # This runs in the normal transaction
    op.alter_column(
        "image_processing_jobs",
        "failure_reason",
        existing_type=sa.String(500),
        type_=sa.Text(),
        existing_nullable=True,
    )

    # Commit the transaction before creating indexes CONCURRENTLY
    # CONCURRENTLY cannot run inside a transaction block
    connection = op.get_bind()
    connection.execute(sa.text("COMMIT"))

    # Create composite index for query optimization (non-blocking)
    connection.execute(
        sa.text(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_image_processing_jobs_query "
            "ON image_processing_jobs (book_id, source_image_id, status)"
        )
    )

    # Create unique partial index to prevent duplicate pending/processing jobs
    connection.execute(
        sa.text(
            "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_image_processing_jobs_pending_unique "
            "ON image_processing_jobs (book_id, source_image_id) "
            "WHERE status IN ('pending', 'processing')"
        )
    )

    # Start a new transaction for any subsequent operations
    connection.execute(sa.text("BEGIN"))


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("COMMIT"))

    connection.execute(
        sa.text("DROP INDEX CONCURRENTLY IF EXISTS ix_image_processing_jobs_pending_unique")
    )
    connection.execute(
        sa.text("DROP INDEX CONCURRENTLY IF EXISTS ix_image_processing_jobs_query")
    )

    connection.execute(sa.text("BEGIN"))

    op.alter_column(
        "image_processing_jobs",
        "failure_reason",
        existing_type=sa.Text(),
        type_=sa.String(500),
        existing_nullable=True,
    )
