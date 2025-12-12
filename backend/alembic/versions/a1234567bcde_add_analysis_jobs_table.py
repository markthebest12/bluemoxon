"""add_analysis_jobs_table

Revision ID: a1234567bcde
Revises: 9d7720474d6d
Create Date: 2025-12-12 22:30:00.000000

Add analysis_jobs table for tracking async Bedrock analysis generation.
This enables background processing to work around API Gateway's 29s timeout.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1234567bcde'
down_revision: str | None = '9d7720474d6d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'analysis_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('book_id', sa.Integer, sa.ForeignKey('books.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('model', sa.String(50), nullable=False, server_default='sonnet'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  onupdate=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Index for querying jobs by book and status
    op.create_index('idx_analysis_jobs_book_status', 'analysis_jobs', ['book_id', 'status'])

    # Partial unique index to prevent multiple active jobs per book
    # Only one job can be 'pending' or 'running' for a given book_id
    op.execute("""
        CREATE UNIQUE INDEX idx_unique_active_job
        ON analysis_jobs(book_id)
        WHERE status IN ('pending', 'running')
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_unique_active_job")
    op.drop_index('idx_analysis_jobs_book_status')
    op.drop_table('analysis_jobs')
