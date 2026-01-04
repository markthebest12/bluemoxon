"""change_analysis_job_model_default_to_opus

Change the database-level default for analysis_jobs.model from 'sonnet' to 'opus'.
This aligns with the Python-level default change in app/constants.py.

Revision ID: 7a6d67bc123e
Revises: d3b3c3c4dd80
Create Date: 2026-01-03 16:47:33.988822

"""
from collections.abc import Sequence

from alembic import op
from app.constants import DEFAULT_ANALYSIS_MODEL

# revision identifiers, used by Alembic.
revision: str = "7a6d67bc123e"
down_revision: str | None = "d3b3c3c4dd80"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "analysis_jobs",
        "model",
        server_default=DEFAULT_ANALYSIS_MODEL,
    )


def downgrade() -> None:
    op.alter_column(
        "analysis_jobs",
        "model",
        server_default="sonnet",
    )
