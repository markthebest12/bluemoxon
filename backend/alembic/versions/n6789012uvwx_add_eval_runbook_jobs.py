"""Add eval_runbook_jobs table for async processing.

Revision ID: n6789012uvwx
Revises: m5678901qrst
Create Date: 2025-12-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "n6789012uvwx"
down_revision = "m5678901qrst"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eval_runbook_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["book_id"],
            ["books.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_eval_runbook_jobs_book_id",
        "eval_runbook_jobs",
        ["book_id"],
    )
    op.create_index(
        "ix_eval_runbook_jobs_status",
        "eval_runbook_jobs",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_eval_runbook_jobs_status", table_name="eval_runbook_jobs")
    op.drop_index("ix_eval_runbook_jobs_book_id", table_name="eval_runbook_jobs")
    op.drop_table("eval_runbook_jobs")
