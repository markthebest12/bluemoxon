"""rerun_condition_grade_normalization

Revision ID: dd7f743834bc
Revises: 57f0cff7af60
Create Date: 2026-01-08 08:56:44.407805

Re-runs the condition_grade normalization that was missed in 44275552664d.
This normalizes legacy values (VG, G, VG+, etc.) to standard enum values
(VERY_GOOD, GOOD, NEAR_FINE, etc.).
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dd7f743834bc"
down_revision: str | None = "57f0cff7af60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Normalize condition_grade values to standard enum set.
    # Uses LOWER() for case-insensitive matching.
    # WHERE clause ensures idempotency - already-normalized rows are skipped.
    op.execute("""
        UPDATE books
        SET condition_grade = CASE LOWER(TRIM(condition_grade))
            -- FINE: pristine/mint condition
            WHEN 'as new' THEN 'FINE'
            WHEN 'mint' THEN 'FINE'
            WHEN 'fine' THEN 'FINE'
            WHEN 'f' THEN 'FINE'
            -- NEAR_FINE: minor wear
            WHEN 'near fine' THEN 'NEAR_FINE'
            WHEN 'nf' THEN 'NEAR_FINE'
            WHEN 'near-fine' THEN 'NEAR_FINE'
            WHEN 'vg+' THEN 'NEAR_FINE'
            WHEN 'vg +' THEN 'NEAR_FINE'
            -- VERY_GOOD: light wear
            WHEN 'very good' THEN 'VERY_GOOD'
            WHEN 'vg' THEN 'VERY_GOOD'
            WHEN 'very-good' THEN 'VERY_GOOD'
            -- GOOD: moderate wear
            WHEN 'vg-' THEN 'GOOD'
            WHEN 'vg -' THEN 'GOOD'
            WHEN 'good+' THEN 'GOOD'
            WHEN 'good +' THEN 'GOOD'
            WHEN 'good' THEN 'GOOD'
            WHEN 'g' THEN 'GOOD'
            WHEN 'vg/g' THEN 'GOOD'
            -- FAIR: heavy wear but readable
            WHEN 'fair' THEN 'FAIR'
            WHEN 'reading copy' THEN 'FAIR'
            -- POOR: significant damage
            WHEN 'poor' THEN 'POOR'
            WHEN 'ex-library' THEN 'POOR'
            WHEN 'ex-lib' THEN 'POOR'
            WHEN 'ex library' THEN 'POOR'
            ELSE condition_grade
        END
        WHERE condition_grade IS NOT NULL
        AND UPPER(condition_grade) NOT IN ('FINE', 'NEAR_FINE', 'VERY_GOOD', 'GOOD', 'FAIR', 'POOR')
    """)


def downgrade() -> None:
    # NO-OP: Data normalization cannot be reversed
    pass
