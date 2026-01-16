"""Add image_processing_jobs table for async background removal.

This table tracks async image processing jobs for background removal.
Similar to analysis_jobs and eval_runbook_jobs.

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-01-16

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e5f6g7h8i9"
down_revision = "c3d4e5f6g7h8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "image_processing_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "book_id",
            sa.Integer,
            sa.ForeignKey("books.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_image_id",
            sa.Integer,
            sa.ForeignKey("book_images.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "processed_image_id",
            sa.Integer,
            sa.ForeignKey("book_images.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("model_used", sa.String(50), nullable=True),
        sa.Column("failure_reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        "ix_image_processing_jobs_book_id",
        "image_processing_jobs",
        ["book_id"],
    )
    op.create_index(
        "ix_image_processing_jobs_status",
        "image_processing_jobs",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_image_processing_jobs_status", table_name="image_processing_jobs")
    op.drop_index("ix_image_processing_jobs_book_id", table_name="image_processing_jobs")
    op.drop_table("image_processing_jobs")
