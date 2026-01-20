"""Add queue_retry_count to image_processing_jobs.

Revision ID: z1234567defg
Revises: 0fc4653fe40b
Create Date: 2026-01-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z1234567defg"
down_revision: str | None = "0fc4653fe40b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add queue_retry_count column to track SQS send retry attempts."""
    op.add_column(
        "image_processing_jobs",
        sa.Column("queue_retry_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Remove queue_retry_count column."""
    op.drop_column("image_processing_jobs", "queue_retry_count")
