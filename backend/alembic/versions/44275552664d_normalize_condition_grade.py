"""normalize_condition_grade

Revision ID: 44275552664d
Revises: 3c8716c1ec04
Create Date: 2026-01-07 18:24:50.857082

This migration normalizes condition_grade values to a standard enum set:
FINE, NEAR_FINE, VERY_GOOD, GOOD, FAIR, POOR

This is a ONE-WAY migration. The downgrade is intentionally a no-op because:
1. The original values vary widely (VG, VG+, VG-, VERY GOOD, etc.)
2. We cannot know which original variant a normalized value came from
3. Data normalization is inherently lossy and should not be reversed

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "44275552664d"
down_revision: str | None = "3c8716c1ec04"
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

    # Backfill NULL condition_grade from book_analyses.condition_assessment JSON
    # when the analysis has a valid condition grade assessment.
    op.execute("""
        UPDATE books
        SET condition_grade = CASE LOWER(TRIM(ba.condition_assessment->>'grade'))
            WHEN 'as new' THEN 'FINE'
            WHEN 'mint' THEN 'FINE'
            WHEN 'fine' THEN 'FINE'
            WHEN 'f' THEN 'FINE'
            WHEN 'near fine' THEN 'NEAR_FINE'
            WHEN 'nf' THEN 'NEAR_FINE'
            WHEN 'near-fine' THEN 'NEAR_FINE'
            WHEN 'vg+' THEN 'NEAR_FINE'
            WHEN 'vg +' THEN 'NEAR_FINE'
            WHEN 'very good' THEN 'VERY_GOOD'
            WHEN 'vg' THEN 'VERY_GOOD'
            WHEN 'very-good' THEN 'VERY_GOOD'
            WHEN 'vg-' THEN 'GOOD'
            WHEN 'vg -' THEN 'GOOD'
            WHEN 'good+' THEN 'GOOD'
            WHEN 'good +' THEN 'GOOD'
            WHEN 'good' THEN 'GOOD'
            WHEN 'g' THEN 'GOOD'
            WHEN 'vg/g' THEN 'GOOD'
            WHEN 'fair' THEN 'FAIR'
            WHEN 'reading copy' THEN 'FAIR'
            WHEN 'poor' THEN 'POOR'
            WHEN 'ex-library' THEN 'POOR'
            WHEN 'ex-lib' THEN 'POOR'
            WHEN 'ex library' THEN 'POOR'
            ELSE NULL
        END
        FROM book_analyses ba
        WHERE books.id = ba.book_id
        AND books.condition_grade IS NULL
        AND ba.condition_assessment->>'grade' IS NOT NULL
    """)


def downgrade() -> None:
    # NO-OP: This is a one-way data normalization migration.
    #
    # We intentionally do NOT reverse this migration because:
    # 1. Original condition values are highly variable (VG, VG+, VG-, VERY GOOD, etc.)
    # 2. Multiple original values map to the same normalized value
    # 3. We cannot determine which original variant a normalized value came from
    # 4. Reverting would require storing the original values, which we don't do
    #
    # If you need to rollback, restore from a database backup taken before this migration.
    pass
