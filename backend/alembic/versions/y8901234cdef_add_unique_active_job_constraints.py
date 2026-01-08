"""add_unique_active_job_constraints

Revision ID: y8901234cdef
Revises: 44275552664d
Create Date: 2026-01-07 18:29:31.876670

Adds partial unique indexes to prevent duplicate active jobs per book.
This prevents the race condition where two simultaneous requests can both
create jobs for the same book.

The partial index only applies to 'pending' and 'running' jobs, so
historical completed/failed jobs are unaffected.

Note: We don't use CONCURRENTLY here because:
1. Alembic migrations run in transactions, and CONCURRENTLY cannot run in a transaction
2. These tables are small (job records, not main data tables)
3. The brief lock is acceptable during deployment windows
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "y8901234cdef"
down_revision: str | None = "44275552664d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create partial unique index for AnalysisJob - only one active job per book
    # This ensures at most one pending/running job exists per book_id
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        ix_analysis_jobs_unique_active_per_book
        ON analysis_jobs (book_id)
        WHERE status IN ('pending', 'running')
        """
    )

    # Create partial unique index for EvalRunbookJob - only one active job per book
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        ix_eval_runbook_jobs_unique_active_per_book
        ON eval_runbook_jobs (book_id)
        WHERE status IN ('pending', 'running')
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_analysis_jobs_unique_active_per_book")
    op.execute("DROP INDEX IF EXISTS ix_eval_runbook_jobs_unique_active_per_book")
