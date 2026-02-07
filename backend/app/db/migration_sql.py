"""Migration SQL constants - single source of truth for database migrations.

This module contains all embedded migration SQL that is used by both:
1. The /health/migrate endpoint (Lambda execution)
2. The migration_verifier.py script (CI verification)

These SQL constants are intentionally embedded rather than calling
alembic.command.upgrade(). This is the correct design for Lambda because:

1. Lambda package only includes app/ and lambdas/ - NOT alembic.ini or alembic/
2. Embedded SQL is self-contained with no external file dependencies
3. All statements use IF NOT EXISTS for idempotency
4. Per-statement results provide visibility into what ran
5. Uses existing db session (no transaction corruption from separate connections)

IMPORTANT: The MIGRATIONS list must be kept in chronological order.
The last entry is used as final_version for alembic_version table.
See health.py run_migrations() for usage.

See: backend/docs/SESSION_LOG_2026-01-04_health_migration_refactor.md
See: GitHub issue #801 for full investigation
"""

from typing import TypedDict


class MigrationDef(TypedDict):
    """Type definition for migration entries. Provides autocomplete and typo detection."""

    id: str
    name: str
    sql_statements: list[str]


# Migration SQL for e44df6ab5669_add_acquisition_columns
MIGRATION_E44DF6AB5669_SQL = [
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS source_url VARCHAR(500)",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS source_item_id VARCHAR(100)",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS estimated_delivery DATE",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS scoring_snapshot JSONB",
    "CREATE INDEX IF NOT EXISTS books_source_item_id_idx ON books (source_item_id)",
]

# Migration SQL for f85b7f976c08_add_scoring_fields
MIGRATION_F85B7F976C08_SQL = [
    "ALTER TABLE authors ADD COLUMN IF NOT EXISTS priority_score INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS investment_grade INTEGER",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS strategic_fit INTEGER",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS collection_impact INTEGER",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS overall_score INTEGER",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS scores_calculated_at TIMESTAMP",
]

# Migration SQL for h8901234efgh_add_is_complete_field
MIGRATION_H8901234EFGH_SQL = [
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS is_complete BOOLEAN NOT NULL DEFAULT TRUE",
]

# Migration SQL for i9012345abcd_add_archive_fields
MIGRATION_I9012345ABCD_SQL = [
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS source_archived_url VARCHAR(500)",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS archive_status VARCHAR(20)",
]

# Migration SQL for 9d7720474d6d_add_admin_config_table
MIGRATION_9D7720474D6D_SQL = [
    """CREATE TABLE IF NOT EXISTS admin_config (
        key VARCHAR(50) PRIMARY KEY,
        value JSONB NOT NULL,
        updated_at TIMESTAMP DEFAULT NOW()
    )""",
    """INSERT INTO admin_config (key, value) VALUES
        ('gbp_to_usd_rate', '1.28'::jsonb),
        ('eur_to_usd_rate', '1.10'::jsonb)
        ON CONFLICT (key) DO NOTHING""",
]

# Migration SQL for a1234567bcde_add_analysis_jobs_table
MIGRATION_A1234567BCDE_SQL = [
    """CREATE TABLE IF NOT EXISTS analysis_jobs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        model VARCHAR(50) NOT NULL DEFAULT 'sonnet',
        error_message TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        completed_at TIMESTAMP WITH TIME ZONE
    )""",
    """CREATE INDEX IF NOT EXISTS idx_analysis_jobs_book_status
        ON analysis_jobs(book_id, status)""",
    """DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'idx_unique_active_job'
        ) THEN
            CREATE UNIQUE INDEX idx_unique_active_job
                ON analysis_jobs(book_id)
                WHERE status IN ('pending', 'running');
        END IF;
    END $$""",
]

# Migration SQL for i0123456abcd_add_binder_tier
MIGRATION_I0123456ABCD_SQL = [
    "ALTER TABLE binders ADD COLUMN IF NOT EXISTS tier VARCHAR(20)",
    # Populate Tier 1 binders (per Victorian Book Acquisition Guide)
    """UPDATE binders SET tier = 'TIER_1'
        WHERE name IN ('Zaehnsdorf', 'Riviere & Son', 'Riviere', 'Sangorski & Sutcliffe',
                       'Sangorski', 'Cobden-Sanderson', 'Bedford') AND tier IS NULL""",
    # Populate Tier 2 binders
    """UPDATE binders SET tier = 'TIER_2'
        WHERE name IN ('Morrell', 'Root & Son', 'Bayntun', 'Tout', 'Stikeman') AND tier IS NULL""",
]

# Migration SQL for j2345678efgh_add_tracking_fields
MIGRATION_J2345678EFGH_SQL = [
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS tracking_number VARCHAR(100)",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS tracking_carrier VARCHAR(50)",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS tracking_url VARCHAR(500)",
]

# Migration SQL for k3456789ijkl_add_ship_date_delivery_end
MIGRATION_K3456789IJKL_SQL = [
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS ship_date DATE",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS estimated_delivery_end DATE",
]

# Migration SQL for l4567890mnop_add_acquisition_cost
MIGRATION_L4567890MNOP_SQL = [
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS acquisition_cost NUMERIC(10,2)",
]

# Migration SQL for m5678901qrst_add_eval_runbook
MIGRATION_M5678901QRST_SQL = [
    """CREATE TABLE IF NOT EXISTS eval_runbooks (
        id SERIAL PRIMARY KEY,
        book_id INTEGER NOT NULL UNIQUE REFERENCES books(id) ON DELETE CASCADE,
        total_score INTEGER NOT NULL,
        score_breakdown JSONB NOT NULL,
        recommendation VARCHAR(20) NOT NULL,
        original_asking_price NUMERIC(10,2),
        current_asking_price NUMERIC(10,2),
        discount_code VARCHAR(100),
        price_notes TEXT,
        fmv_low NUMERIC(10,2),
        fmv_high NUMERIC(10,2),
        recommended_price NUMERIC(10,2),
        ebay_comparables JSONB,
        abebooks_comparables JSONB,
        condition_grade VARCHAR(20),
        condition_positives JSONB,
        condition_negatives JSONB,
        critical_issues JSONB,
        analysis_narrative TEXT,
        item_identification JSONB,
        generated_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS ix_eval_runbooks_book_id ON eval_runbooks(book_id)",
    """CREATE TABLE IF NOT EXISTS eval_price_history (
        id SERIAL PRIMARY KEY,
        eval_runbook_id INTEGER NOT NULL REFERENCES eval_runbooks(id) ON DELETE CASCADE,
        previous_price NUMERIC(10,2),
        new_price NUMERIC(10,2),
        discount_code VARCHAR(100),
        notes TEXT,
        score_before INTEGER,
        score_after INTEGER,
        changed_at TIMESTAMP DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS ix_eval_price_history_runbook_id ON eval_price_history(eval_runbook_id)",
]

# Migration SQL for n6789012uvwx_add_eval_runbook_jobs
MIGRATION_N6789012UVWX_SQL = [
    """CREATE TABLE IF NOT EXISTS eval_runbook_jobs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        error_message TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        completed_at TIMESTAMP WITH TIME ZONE
    )""",
    "CREATE INDEX IF NOT EXISTS ix_eval_runbook_jobs_book_id ON eval_runbook_jobs(book_id)",
    "CREATE INDEX IF NOT EXISTS ix_eval_runbook_jobs_status ON eval_runbook_jobs(status)",
]

# Migration SQL for o7890123wxyz_add_fmv_notes_and_confidence
MIGRATION_O7890123WXYZ_SQL = [
    "ALTER TABLE eval_runbooks ADD COLUMN IF NOT EXISTS fmv_notes TEXT",
    "ALTER TABLE eval_runbooks ADD COLUMN IF NOT EXISTS fmv_confidence VARCHAR(20)",
]

# Migration SQL for p8901234yzab_add_tracking_status_fields
MIGRATION_P8901234YZAB_SQL = [
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS tracking_status VARCHAR(100)",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS tracking_last_checked TIMESTAMP WITH TIME ZONE",
]

# Migration SQL for q0123456cdef_add_provenance_first_edition
MIGRATION_Q0123456CDEF_SQL = [
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS is_first_edition BOOLEAN",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS has_provenance BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS provenance_tier VARCHAR(20)",
    "CREATE INDEX IF NOT EXISTS books_is_first_edition_idx ON books (is_first_edition)",
    "CREATE INDEX IF NOT EXISTS books_has_provenance_idx ON books (has_provenance)",
    "CREATE INDEX IF NOT EXISTS books_provenance_tier_idx ON books (provenance_tier)",
]

# Migration SQL for r1234567ghij_add_extraction_status
MIGRATION_R1234567GHIJ_SQL = [
    "ALTER TABLE book_analyses ADD COLUMN IF NOT EXISTS extraction_status VARCHAR(20)",
]

# Migration SQL for s2345678klmn_add_author_tier
# NOTE: This migration also includes expand_binding_type SQL that was incorrectly
# listed separately in the original health.py with the same ID. Combined here
# to fix the duplicate ID issue while preserving the SQL for idempotent execution.
MIGRATION_S2345678KLMN_SQL = [
    # Originally listed as separate "expand_binding_type" migration with same ID
    "ALTER TABLE books ALTER COLUMN binding_type TYPE VARCHAR(100)",
    # The actual alembic migration: add author tier
    "ALTER TABLE authors ADD COLUMN IF NOT EXISTS tier VARCHAR(10)",
]

# Migration SQL for t3456789lmno_expand_binder_name
MIGRATION_T3456789LMNO_SQL = [
    "ALTER TABLE binders ALTER COLUMN name TYPE VARCHAR(100)",
]

# Migration SQL for 6e90a0c87832_add_tiered_recommendation_fields
MIGRATION_6E90A0C87832_SQL = [
    "ALTER TABLE eval_runbooks ADD COLUMN IF NOT EXISTS recommendation_tier VARCHAR(20)",
    "ALTER TABLE eval_runbooks ADD COLUMN IF NOT EXISTS quality_score INTEGER",
    "ALTER TABLE eval_runbooks ADD COLUMN IF NOT EXISTS strategic_fit_score INTEGER",
    "ALTER TABLE eval_runbooks ADD COLUMN IF NOT EXISTS combined_score INTEGER",
    "ALTER TABLE eval_runbooks ADD COLUMN IF NOT EXISTS price_position VARCHAR(20)",
    "ALTER TABLE eval_runbooks ADD COLUMN IF NOT EXISTS suggested_offer NUMERIC(10,2)",
    "ALTER TABLE eval_runbooks ADD COLUMN IF NOT EXISTS recommendation_reasoning VARCHAR(500)",
    """ALTER TABLE eval_runbooks ADD COLUMN IF NOT EXISTS strategic_floor_applied
        BOOLEAN NOT NULL DEFAULT FALSE""",
    """ALTER TABLE eval_runbooks ADD COLUMN IF NOT EXISTS quality_floor_applied
        BOOLEAN NOT NULL DEFAULT FALSE""",
    """ALTER TABLE eval_runbooks ADD COLUMN IF NOT EXISTS scoring_version
        VARCHAR(20) NOT NULL DEFAULT '2025-01'""",
    """ALTER TABLE eval_runbooks ADD COLUMN IF NOT EXISTS score_source
        VARCHAR(20) NOT NULL DEFAULT 'eval_runbook'""",
    "ALTER TABLE eval_runbooks ADD COLUMN IF NOT EXISTS last_scored_price NUMERIC(10,2)",
    "ALTER TABLE eval_runbooks ADD COLUMN IF NOT EXISTS napoleon_recommendation VARCHAR(20)",
    "ALTER TABLE eval_runbooks ADD COLUMN IF NOT EXISTS napoleon_reasoning TEXT",
    "ALTER TABLE eval_runbooks ADD COLUMN IF NOT EXISTS napoleon_analyzed_at TIMESTAMP",
]

# NOTE: MIGRATION_S2345678KLMN_AUTHOR_TIER_SQL removed - combined into MIGRATION_S2345678KLMN_SQL
# to fix duplicate ID issue. See comment above MIGRATION_S2345678KLMN_SQL.

# Migration SQL for f4f2fbe81faa_seed_author_publisher_binder_tiers (data)
MIGRATION_F4F2FBE81FAA_SEED_TIERS_SQL = [
    # Author tiers
    "UPDATE authors SET tier = 'TIER_1' WHERE id = 34",  # Darwin
    "UPDATE authors SET tier = 'TIER_2' WHERE id = 250",  # Dickens
    "UPDATE authors SET tier = 'TIER_2' WHERE id = 335",  # Collins
    "UPDATE authors SET tier = 'TIER_3' WHERE id = 260",  # Ruskin
    # Publisher tiers
    "UPDATE publishers SET tier = 'TIER_2' WHERE id = 193",  # Chatto and Windus
    "UPDATE publishers SET tier = 'TIER_2' WHERE id = 197",  # George Allen
    # Binder tier updates
    "UPDATE binders SET tier = 'TIER_1' WHERE id = 4",  # Bayntun upgrade
    "UPDATE binders SET tier = 'TIER_1' WHERE id = 27",  # Leighton
]

# Migration SQL for t3456789opqr_add_preferred_to_entities
MIGRATION_T3456789OPQR_SQL = [
    "ALTER TABLE authors ADD COLUMN IF NOT EXISTS preferred BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE publishers ADD COLUMN IF NOT EXISTS preferred BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE binders ADD COLUMN IF NOT EXISTS preferred BOOLEAN NOT NULL DEFAULT FALSE",
]

# Migration SQL for u4567890stuv_add_archive_attempts
MIGRATION_U4567890STUV_SQL = [
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS archive_attempts INTEGER NOT NULL DEFAULT 0",
]

# Migration SQL for v5678901uvwx_add_source_expired
MIGRATION_V5678901UVWX_SQL = [
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS source_expired BOOLEAN",
]

# Migration SQL for 5d2aef44594e_add_model_id_to_analyses
MIGRATION_5D2AEF44594E_SQL = [
    "ALTER TABLE book_analyses ADD COLUMN IF NOT EXISTS model_id VARCHAR(100)",
]

# Migration SQL for w6789012wxyz_add_carrier_api_support
MIGRATION_W6789012WXYZ_SQL = [
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS tracking_active BOOLEAN DEFAULT FALSE",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS tracking_delivered_at TIMESTAMPTZ",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_tracking_email BOOLEAN DEFAULT TRUE",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_tracking_sms BOOLEAN DEFAULT FALSE",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20)",
    """CREATE TABLE IF NOT EXISTS notifications (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        book_id INTEGER REFERENCES books(id) ON DELETE SET NULL,
        message TEXT NOT NULL,
        read BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications (user_id, read) WHERE read = false",
]

# Migration SQL for x7890123abcd_phone_e164_constraint
MIGRATION_X7890123ABCD_SQL = [
    """DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'users_phone_number_e164'
        ) THEN
            ALTER TABLE users
            ADD CONSTRAINT users_phone_number_e164
            CHECK (phone_number IS NULL OR phone_number ~ '^\\+[1-9]\\d{1,14}$');
        END IF;
    END $$""",
    """CREATE TABLE IF NOT EXISTS carrier_circuit_state (
        carrier_name VARCHAR(50) PRIMARY KEY,
        failure_count INTEGER NOT NULL DEFAULT 0,
        last_failure_at TIMESTAMPTZ,
        circuit_open_until TIMESTAMPTZ,
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )""",
]

# Migration SQL for d3b3c3c4dd80_backfill_tracking_active_for_in_transit_books
# Data migration - sets tracking_active=true for existing in-transit books with tracking numbers
MIGRATION_D3B3C3C4DD80_SQL = [
    """UPDATE books
       SET tracking_active = true
       WHERE tracking_number IS NOT NULL
         AND status = 'IN_TRANSIT'
         AND tracking_active = false""",
]

# Migration SQL for 7a6d67bc123e_change_analysis_job_model_default_to_opus
# Changes the database-level default for analysis_jobs.model from 'sonnet' to 'opus'
MIGRATION_7A6D67BC123E_SQL = [
    "ALTER TABLE analysis_jobs ALTER COLUMN model SET DEFAULT 'opus'",
]

# Migration SQL for 3c8716c1ec04_add_publisher_aliases_table
# Creates publisher_aliases table for mapping variant names to canonical publishers
MIGRATION_3C8716C1EC04_SQL = [
    """CREATE TABLE IF NOT EXISTS publisher_aliases (
        id SERIAL PRIMARY KEY,
        alias_name VARCHAR(200) UNIQUE NOT NULL,
        publisher_id INTEGER NOT NULL REFERENCES publishers(id) ON DELETE CASCADE
    )""",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_publisher_aliases_alias_name ON publisher_aliases(alias_name)",
    "CREATE INDEX IF NOT EXISTS ix_publisher_aliases_alias_name_lower ON publisher_aliases (LOWER(alias_name))",
    "CREATE INDEX IF NOT EXISTS ix_publisher_aliases_publisher_id ON publisher_aliases(publisher_id)",
]

# Migration SQL for 44275552664d_normalize_condition_grade
# INTENTIONALLY EMPTY: The original condition_grade normalization via Alembic
# missed some records. This entry exists to maintain alembic_version ordering.
# The actual normalization SQL is in dd7f743834bc (rerun_condition_grade_normalization)
# and 21eb898ba04b (add_missing_condition_grade_mappings).
MIGRATION_44275552664D_SQL: list[str] = []

# Migration SQL for 57f0cff7af60_add_unique_active_job_constraints
# Creates partial unique indexes to prevent duplicate active jobs per book
MIGRATION_57F0CFF7AF60_SQL = [
    """CREATE UNIQUE INDEX IF NOT EXISTS
       ix_analysis_jobs_unique_active_per_book
       ON analysis_jobs (book_id)
       WHERE status IN ('pending', 'running')""",
    """CREATE UNIQUE INDEX IF NOT EXISTS
       ix_eval_runbook_jobs_unique_active_per_book
       ON eval_runbook_jobs (book_id)
       WHERE status IN ('pending', 'running')""",
]

# Migration SQL for dd7f743834bc_rerun_condition_grade_normalization
# Re-runs condition_grade normalization that was missed in 44275552664d
MIGRATION_DD7F743834BC_SQL = [
    """UPDATE books
       SET condition_grade = CASE LOWER(TRIM(condition_grade))
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
           ELSE condition_grade
       END
       WHERE condition_grade IS NOT NULL
       AND UPPER(condition_grade) NOT IN ('FINE', 'NEAR_FINE', 'VERY_GOOD', 'GOOD', 'FAIR', 'POOR')""",
]

# Migration SQL for 21eb898ba04b_add_missing_condition_grade_mappings
# Adds missing condition_grade mappings not covered in dd7f743834bc
MIGRATION_21EB898BA04B_SQL = [
    """UPDATE books
       SET condition_grade = CASE LOWER(TRIM(condition_grade))
           WHEN 'g+' THEN 'GOOD'
           WHEN 'g +' THEN 'GOOD'
           WHEN 'g-' THEN 'FAIR'
           WHEN 'g -' THEN 'FAIR'
           WHEN 'good-' THEN 'FAIR'
           WHEN 'good -' THEN 'FAIR'
           WHEN 'nf-' THEN 'VERY_GOOD'
           WHEN 'nf -' THEN 'VERY_GOOD'
           WHEN 'nf+' THEN 'FINE'
           WHEN 'nf +' THEN 'FINE'
           WHEN 'f-' THEN 'NEAR_FINE'
           WHEN 'f -' THEN 'NEAR_FINE'
           WHEN 'f+' THEN 'FINE'
           WHEN 'f +' THEN 'FINE'
           WHEN 'vgc' THEN 'VERY_GOOD'
           WHEN 'gc' THEN 'GOOD'
           WHEN 'fc' THEN 'FAIR'
           ELSE condition_grade
       END
       WHERE condition_grade IS NOT NULL
       AND UPPER(condition_grade) NOT IN ('FINE', 'NEAR_FINE', 'VERY_GOOD', 'GOOD', 'FAIR', 'POOR')""",
]

# Migration SQL for 88779697decb_backfill_roi_pct
# Backfill roi_pct for existing books that have both value_mid and acquisition_cost
MIGRATION_88779697DECB_SQL = [
    """UPDATE books
       SET roi_pct = ROUND(((value_mid - acquisition_cost) / acquisition_cost) * 100, 2)
       WHERE value_mid IS NOT NULL
         AND acquisition_cost IS NOT NULL
         AND acquisition_cost > 0
         AND roi_pct IS NULL""",
]

# Migration SQL for y8901234bcde_add_unique_constraint_to_author_name
# Adds unique constraint to author.name to prevent duplicate authors
MIGRATION_Y8901234BCDE_SQL = [
    """DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'uq_authors_name'
        ) THEN
            ALTER TABLE authors
            ADD CONSTRAINT uq_authors_name UNIQUE (name);
        END IF;
    END $$""",
]

# Migration SQL for 5bd4bb0308b4_normalize_condition_grade_casing
# Normalizes condition_grade values to UPPERCASE for consistency
# Backup column is created, used, then cleaned up
MIGRATION_5BD4BB0308B4_SQL = [
    """ALTER TABLE books ADD COLUMN IF NOT EXISTS _condition_grade_backup VARCHAR(20)""",
    """UPDATE books SET _condition_grade_backup = condition_grade
       WHERE condition_grade IS NOT NULL AND _condition_grade_backup IS NULL""",
    """UPDATE books SET condition_grade = UPPER(condition_grade)
       WHERE condition_grade IS NOT NULL AND condition_grade != UPPER(condition_grade)""",
    # Cleanup: drop backup column after successful migration
    """ALTER TABLE books DROP COLUMN IF EXISTS _condition_grade_backup""",
]

# Migration SQL for z0012345cdef_add_cleanup_jobs_table
# Creates cleanup_jobs table for tracking async cleanup operations
MIGRATION_Z0012345CDEF_SQL = [
    """CREATE TABLE IF NOT EXISTS cleanup_jobs (
        id UUID PRIMARY KEY,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        total_count INTEGER NOT NULL DEFAULT 0,
        total_bytes BIGINT NOT NULL DEFAULT 0,
        deleted_count INTEGER NOT NULL DEFAULT 0,
        deleted_bytes BIGINT NOT NULL DEFAULT 0,
        error_message TEXT,
        created_at TIMESTAMP WITH TIME ZONE,
        updated_at TIMESTAMP WITH TIME ZONE,
        completed_at TIMESTAMP WITH TIME ZONE
    )""",
    "CREATE INDEX IF NOT EXISTS ix_cleanup_jobs_status ON cleanup_jobs(status)",
]

# Migration SQL for a1f2e3d4c5b6_add_failed_count_to_cleanup_jobs
# Adds failed_count column to track partial failures during batch delete
MIGRATION_Z1012345EFGH_SQL = [
    "ALTER TABLE cleanup_jobs ADD COLUMN IF NOT EXISTS failed_count INTEGER NOT NULL DEFAULT 0",
]

# Migration SQL for b2c3d4e5f6a7_add_binder_operation_years
# Adds founded_year and closed_year columns to binders table for tooltip display
MIGRATION_Z2012345GHIJ_SQL = [
    "ALTER TABLE binders ADD COLUMN IF NOT EXISTS founded_year INTEGER",
    "ALTER TABLE binders ADD COLUMN IF NOT EXISTS closed_year INTEGER",
]

# Migration SQL for c3d4e5f6g7h8_add_is_background_processed_to_book_images
# Adds flag indicating whether an image has had its background digitally processed
MIGRATION_C3D4E5F6G7H8_SQL = [
    "ALTER TABLE book_images ADD COLUMN IF NOT EXISTS is_background_processed BOOLEAN NOT NULL DEFAULT FALSE",
]

# Migration SQL for d4e5f6g7h8i9_add_image_processing_jobs_table
# Tracks async image processing jobs for background removal
MIGRATION_D4E5F6G7H8I9_SQL = [
    """CREATE TABLE IF NOT EXISTS image_processing_jobs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
        source_image_id INTEGER REFERENCES book_images(id) ON DELETE SET NULL,
        processed_image_id INTEGER REFERENCES book_images(id) ON DELETE SET NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        attempt_count INTEGER NOT NULL DEFAULT 0,
        model_used VARCHAR(50),
        failure_reason VARCHAR(500),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        completed_at TIMESTAMP WITH TIME ZONE
    )""",
    "CREATE INDEX IF NOT EXISTS ix_image_processing_jobs_book_id ON image_processing_jobs(book_id)",
    "CREATE INDEX IF NOT EXISTS ix_image_processing_jobs_status ON image_processing_jobs(status)",
]

# Migration SQL for 0fc4653fe40b_add_image_processing_indexes_and_fix_failure_reason
# Adds indexes and changes failure_reason to TEXT
# Note: Uses regular CREATE INDEX (not CONCURRENTLY) for health.py compatibility
MIGRATION_0FC4653FE40B_SQL = [
    "ALTER TABLE image_processing_jobs ALTER COLUMN failure_reason TYPE TEXT",
    "CREATE INDEX IF NOT EXISTS ix_image_processing_jobs_query ON image_processing_jobs(book_id, source_image_id, status)",
    """DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'ix_image_processing_jobs_pending_unique'
        ) THEN
            CREATE UNIQUE INDEX ix_image_processing_jobs_pending_unique
                ON image_processing_jobs(book_id, source_image_id)
                WHERE status IN ('pending', 'processing');
        END IF;
    END $$""",
]

# Migration SQL for z1234567defg_add_queue_retry_count
# Adds queue_retry_count column for tracking SQS send retry attempts
MIGRATION_Z1234567DEFG_SQL = [
    "ALTER TABLE image_processing_jobs ADD COLUMN IF NOT EXISTS queue_retry_count INTEGER NOT NULL DEFAULT 0",
]

# Migration SQL for z2345678ghij_add_fk_indexes_for_eager_loading
# Adds indexes on FK columns for correlated subquery optimization (issue #1239)
MIGRATION_Z2345678GHIJ_SQL = [
    "CREATE INDEX IF NOT EXISTS books_author_id_idx ON books (author_id)",
    "CREATE INDEX IF NOT EXISTS books_publisher_id_idx ON books (publisher_id)",
    "CREATE INDEX IF NOT EXISTS books_binder_id_idx ON books (binder_id)",
]

# Tables with auto-increment sequences for g7890123def0_fix_sequence_sync
# Note: Only include tables that already exist. New tables (eval_runbooks, eval_price_history)
# don't need sequence sync since they start fresh with id=1.
TABLES_WITH_SEQUENCES = [
    "authors",
    "api_keys",
    "binders",
    "book_analyses",
    "book_images",
    "books",
    "publishers",
    "users",
]


# SQL to clean up orphaned records (no matching book_id in books table)
CLEANUP_ORPHANS_SQL = [
    # Delete orphaned analyses
    """DELETE FROM book_analyses
       WHERE book_id NOT IN (SELECT id FROM books)""",
    # Delete orphaned eval runbooks
    """DELETE FROM eval_runbooks
       WHERE book_id NOT IN (SELECT id FROM books)""",
    # Delete orphaned book images
    """DELETE FROM book_images
       WHERE book_id NOT IN (SELECT id FROM books)""",
    # Delete orphaned analysis jobs
    """DELETE FROM analysis_jobs
       WHERE book_id NOT IN (SELECT id FROM books)""",
    # Delete orphaned eval runbook jobs
    """DELETE FROM eval_runbook_jobs
       WHERE book_id NOT IN (SELECT id FROM books)""",
]


# Complete list of all migrations with their IDs, names, and SQL statements.
# This is the authoritative list used by health.py and migration_verifier.py.
#
# CRITICAL: Maintain chronological order! The LAST entry becomes final_version
# in alembic_version table. Out-of-order entries cause version drift.
#
# CRITICAL: IDs must be unique! Duplicate IDs cause silent failures.
# See test_migration_ids_are_unique() for CI enforcement.
# Migration SQL for e5f6g7h8i9j0_add_entity_profiles_table
# Creates entity_profiles table for caching AI-generated biographical content
MIGRATION_E5F6G7H8I9J0_SQL = [
    """CREATE TABLE IF NOT EXISTS entity_profiles (
        id SERIAL PRIMARY KEY,
        entity_type VARCHAR(20) NOT NULL,
        entity_id INTEGER NOT NULL,
        bio_summary TEXT,
        personal_stories JSON,
        connection_narratives JSON,
        generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
        model_version VARCHAR(100),
        owner_id INTEGER NOT NULL REFERENCES users(id)
    )""",
    """DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'uq_entity_profile'
        ) THEN
            ALTER TABLE entity_profiles
            ADD CONSTRAINT uq_entity_profile UNIQUE (entity_type, entity_id, owner_id);
        END IF;
    END $$""",
]

MIGRATION_F6G7H8I9J0K1_SQL = [
    """ALTER TABLE entity_profiles
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()""",
    """ALTER TABLE entity_profiles
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()""",
    """UPDATE entity_profiles SET created_at = generated_at, updated_at = generated_at
    WHERE created_at = updated_at""",
]

MIGRATION_G7H8I9J0K1L2_SQL = [
    "ALTER TABLE entity_profiles ADD COLUMN IF NOT EXISTS relationship_stories JSON",
]

# Migration SQL for h8i9j0k1l2m3_add_profile_generation_jobs
MIGRATION_H8I9J0K1L2M3_SQL = [
    """CREATE TABLE IF NOT EXISTS profile_generation_jobs (
        id VARCHAR(36) PRIMARY KEY,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        owner_id INTEGER NOT NULL REFERENCES users(id),
        total_entities INTEGER NOT NULL DEFAULT 0,
        succeeded INTEGER NOT NULL DEFAULT 0,
        failed INTEGER NOT NULL DEFAULT 0,
        error_log TEXT,
        completed_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS ix_profile_generation_jobs_status ON profile_generation_jobs (status)",
]

# Migration SQL for z3456789ijkl_add_image_url_to_entity_tables
# Adds image_url column to authors, publishers, binders for portrait images (#1632)
MIGRATION_Z3456789IJKL_SQL = [
    "ALTER TABLE authors ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)",
    "ALTER TABLE publishers ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)",
    "ALTER TABLE binders ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)",
]

# Migration SQL for 184855af397c_narrow_entity_profile_unique_constraint
MIGRATION_184855AF397C_SQL = [
    # Deduplicate: keep most recently updated profile per (entity_type, entity_id)
    """DELETE FROM entity_profiles
    WHERE id NOT IN (
        SELECT DISTINCT ON (entity_type, entity_id) id
        FROM entity_profiles
        ORDER BY entity_type, entity_id, updated_at DESC NULLS LAST
    )""",
    # Drop old constraint that included owner_id
    "ALTER TABLE entity_profiles DROP CONSTRAINT IF EXISTS uq_entity_profile",
    # Add new constraint on (entity_type, entity_id) only
    """DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'uq_entity_profile'
        ) THEN
            ALTER TABLE entity_profiles
            ADD CONSTRAINT uq_entity_profile UNIQUE (entity_type, entity_id);
        END IF;
    END $$""",
]

# Migration f7624c3b4e76: Drop owner_id from entity_profiles (#1765)
MIGRATION_F7624C3B4E76_SQL: list[str] = [
    "ALTER TABLE entity_profiles DROP COLUMN IF EXISTS owner_id",
]

# Migration SQL for 708c5a15f5bb_add_app_config_table
# Creates app_config table for runtime key-value configuration (model selectors, etc.)
MIGRATION_708C5A15F5BB_SQL = [
    """CREATE TABLE IF NOT EXISTS app_config (
        key VARCHAR(100) PRIMARY KEY,
        value VARCHAR(500) NOT NULL,
        description VARCHAR(500),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_by VARCHAR(100)
    )""",
]

# Migration SQL for z4567890klmn_consolidate_config_tables
# Merges admin_config rows into app_config and drops admin_config table (#1776)
MIGRATION_Z4567890KLMN_SQL = [
    """INSERT INTO app_config (key, value, description, updated_at)
       SELECT key,
              TRIM(BOTH '"' FROM value::text),
              'Migrated from admin_config',
              updated_at
       FROM admin_config
       ON CONFLICT (key) DO NOTHING""",
    "DROP TABLE IF EXISTS admin_config",
]

MIGRATION_E9A5101C8557_SQL = [
    "ALTER TABLE entity_profiles ADD COLUMN IF NOT EXISTS ai_connections JSON",
]

# Migration SQL for 2843f260f764_add_ai_connections_table
# Creates canonical relational table for AI-discovered personal connections (#1813)
MIGRATION_2843F260F764_SQL = [
    """CREATE TABLE IF NOT EXISTS ai_connections (
        id SERIAL PRIMARY KEY,
        source_type VARCHAR(20) NOT NULL,
        source_id INTEGER NOT NULL,
        target_type VARCHAR(20) NOT NULL,
        target_id INTEGER NOT NULL,
        relationship VARCHAR(20) NOT NULL,
        sub_type VARCHAR(50),
        confidence FLOAT NOT NULL DEFAULT 0.5,
        evidence TEXT,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )""",
    """DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'uq_ai_connection'
        ) THEN
            ALTER TABLE ai_connections
            ADD CONSTRAINT uq_ai_connection
            UNIQUE (source_type, source_id, target_type, target_id, relationship);
        END IF;
    END $$""",
    "CREATE INDEX IF NOT EXISTS ix_ai_connections_source ON ai_connections (source_type, source_id)",
    "CREATE INDEX IF NOT EXISTS ix_ai_connections_target ON ai_connections (target_type, target_id)",
    # Data migration: copy existing JSON into the new table.
    # Uses DISTINCT ON to deduplicate A→B / B→A pairs that resolve to the
    # same canonical key, keeping the row with the highest confidence.
    """INSERT INTO ai_connections (
        source_type, source_id, target_type, target_id,
        relationship, sub_type, confidence, evidence
    )
    SELECT DISTINCT ON (source_type, source_id, target_type, target_id, relationship)
        source_type, source_id, target_type, target_id,
        relationship, sub_type, confidence, evidence
    FROM (
        SELECT
            CASE WHEN (ep.entity_type || ':' || CAST(ep.entity_id AS TEXT))
                      <= (c.target_type || ':' || CAST(c.target_id AS TEXT))
                 THEN ep.entity_type
                 ELSE c.target_type
            END AS source_type,
            CASE WHEN (ep.entity_type || ':' || CAST(ep.entity_id AS TEXT))
                      <= (c.target_type || ':' || CAST(c.target_id AS TEXT))
                 THEN ep.entity_id
                 ELSE c.target_id
            END AS source_id,
            CASE WHEN (ep.entity_type || ':' || CAST(ep.entity_id AS TEXT))
                      <= (c.target_type || ':' || CAST(c.target_id AS TEXT))
                 THEN c.target_type
                 ELSE ep.entity_type
            END AS target_type,
            CASE WHEN (ep.entity_type || ':' || CAST(ep.entity_id AS TEXT))
                      <= (c.target_type || ':' || CAST(c.target_id AS TEXT))
                 THEN c.target_id
                 ELSE ep.entity_id
            END AS target_id,
            c.relationship,
            c.sub_type,
            COALESCE(c.confidence, 0.5) AS confidence,
            c.evidence
        FROM (
                SELECT entity_type, entity_id, ai_connections
                FROM entity_profiles
                WHERE ai_connections IS NOT NULL
                  AND jsonb_typeof(ai_connections::jsonb) = 'array'
             ) ep,
             jsonb_to_recordset(ep.ai_connections::jsonb) AS c(
                 target_type text,
                 target_id integer,
                 relationship text,
                 sub_type text,
                 confidence float,
                 evidence text
             )
        WHERE c.relationship IS NOT NULL
          AND c.target_type IS NOT NULL
          AND c.target_id IS NOT NULL
    ) AS raw
    ORDER BY source_type, source_id, target_type, target_id, relationship,
             confidence DESC
    ON CONFLICT (source_type, source_id, target_type, target_id, relationship)
    DO NOTHING""",
]

# Migration SQL for 7a3a9a604ccf_null_broken_portrait_image_urls
# After S3 portrait cleanup (2026-02-06), ~106 publishers+binders still had
# image_url pointing to deleted S3 files. NULL them out so frontend falls back
# to placeholder images. Only keep image_url for entities with verified portraits.
# IDs derived from manual S3 audit: publishers with verified Wikidata matches or
# manually curated images, binders with verified Wikidata matches.
# Scoped to CDN portrait URLs to avoid re-nulling future manual uploads.
MIGRATION_7A3A9A604CCF_SQL = [
    """UPDATE publishers
    SET image_url = NULL
    WHERE id NOT IN (12, 32, 33, 166, 167, 168, 175, 193, 197, 231, 243, 244, 254)
      AND image_url IS NOT NULL
      AND image_url LIKE '%/entities/publisher/%/portrait.jpg'""",
    """UPDATE binders
    SET image_url = NULL
    WHERE id NOT IN (49, 69, 76)
      AND image_url IS NOT NULL
      AND image_url LIKE '%/entities/binder/%/portrait.jpg'""",
]

# Migration SQL for b3c8d2e1f4a7_backfill_entity_founded_years
# Backfill founded_year for binders missing this data. Years sourced from
# DNB, Wikipedia, and firm histories. Uses COALESCE to avoid overwriting
# any values set via other means.
MIGRATION_B3C8D2E1F4A7_SQL = [
    # Binders — years sourced from DNB, Wikipedia, firm histories
    # Riviere & Son: Robert Riviere started bindery in Bath 1829
    "UPDATE binders SET founded_year = 1829 WHERE id = 15 AND founded_year IS NULL",
    # Zaehnsdorf: Joseph Zaehnsdorf opened shop in London 1842
    "UPDATE binders SET founded_year = 1842 WHERE id = 2 AND founded_year IS NULL",
    # Sangorski & Sutcliffe: formally established 1 October 1901
    "UPDATE binders SET founded_year = 1901 WHERE id = 9 AND founded_year IS NULL",
    # Bayntun: George Bayntun started in Bath 1894
    "UPDATE binders SET founded_year = 1894 WHERE id = 4 AND founded_year IS NULL",
    # Bedford: Francis Bedford went independent 1851
    "UPDATE binders SET founded_year = 1851 WHERE id = 86 AND founded_year IS NULL",
    # Doves Bindery: Cobden-Sanderson established at Hammersmith 1893
    "UPDATE binders SET founded_year = 1893 WHERE id = 70 AND founded_year IS NULL",
    # Hayday: James Hayday rented premises at Little Queen St 1833
    "UPDATE binders SET founded_year = 1833 WHERE id = 60 AND founded_year IS NULL",
    # Leighton: Archibald Leighton founded firm c.1764
    "UPDATE binders SET founded_year = 1764 WHERE id = 27 AND founded_year IS NULL",
]

MIGRATIONS: list[MigrationDef] = [
    {
        "id": "e44df6ab5669",
        "name": "add_acquisition_columns",
        "sql_statements": MIGRATION_E44DF6AB5669_SQL,
    },
    {
        "id": "f85b7f976c08",
        "name": "add_scoring_fields",
        "sql_statements": MIGRATION_F85B7F976C08_SQL,
    },
    {
        "id": "g7890123def0",
        "name": "fix_sequence_sync",
        "sql_statements": [],  # Dynamic SQL, handled specially
    },
    {
        "id": "h8901234efgh",
        "name": "add_is_complete_field",
        "sql_statements": MIGRATION_H8901234EFGH_SQL,
    },
    {
        "id": "i9012345abcd",
        "name": "add_archive_fields",
        "sql_statements": MIGRATION_I9012345ABCD_SQL,
    },
    {
        "id": "9d7720474d6d",
        "name": "add_admin_config_table",
        "sql_statements": MIGRATION_9D7720474D6D_SQL,
    },
    {
        "id": "a1234567bcde",
        "name": "add_analysis_jobs_table",
        "sql_statements": MIGRATION_A1234567BCDE_SQL,
    },
    {
        "id": "i0123456abcd",
        "name": "add_binder_tier",
        "sql_statements": MIGRATION_I0123456ABCD_SQL,
    },
    {
        "id": "j2345678efgh",
        "name": "add_tracking_fields",
        "sql_statements": MIGRATION_J2345678EFGH_SQL,
    },
    {
        "id": "k3456789ijkl",
        "name": "add_ship_date_delivery_end",
        "sql_statements": MIGRATION_K3456789IJKL_SQL,
    },
    {
        "id": "l4567890mnop",
        "name": "add_acquisition_cost",
        "sql_statements": MIGRATION_L4567890MNOP_SQL,
    },
    {
        "id": "m5678901qrst",
        "name": "add_eval_runbook",
        "sql_statements": MIGRATION_M5678901QRST_SQL,
    },
    {
        "id": "n6789012uvwx",
        "name": "add_eval_runbook_jobs",
        "sql_statements": MIGRATION_N6789012UVWX_SQL,
    },
    {
        "id": "o7890123wxyz",
        "name": "add_fmv_notes_and_confidence",
        "sql_statements": MIGRATION_O7890123WXYZ_SQL,
    },
    {
        "id": "p8901234yzab",
        "name": "add_tracking_status_fields",
        "sql_statements": MIGRATION_P8901234YZAB_SQL,
    },
    {
        "id": "q0123456cdef",
        "name": "add_provenance_first_edition",
        "sql_statements": MIGRATION_Q0123456CDEF_SQL,
    },
    {
        "id": "r1234567ghij",
        "name": "add_extraction_status",
        "sql_statements": MIGRATION_R1234567GHIJ_SQL,
    },
    {
        "id": "t3456789lmno",
        "name": "expand_binder_name",
        "sql_statements": MIGRATION_T3456789LMNO_SQL,
    },
    {
        "id": "6e90a0c87832",
        "name": "add_tiered_recommendation_fields",
        "sql_statements": MIGRATION_6E90A0C87832_SQL,
    },
    {
        # Combined expand_binding_type + add_author_tier (both had same ID in health.py)
        "id": "s2345678klmn",
        "name": "add_author_tier_and_expand_binding_type",
        "sql_statements": MIGRATION_S2345678KLMN_SQL,
    },
    {
        "id": "f4f2fbe81faa",
        "name": "seed_author_publisher_binder_tiers",
        "sql_statements": MIGRATION_F4F2FBE81FAA_SEED_TIERS_SQL,
    },
    {
        "id": "t3456789opqr",
        "name": "add_preferred_to_entities",
        "sql_statements": MIGRATION_T3456789OPQR_SQL,
    },
    {
        "id": "u4567890stuv",
        "name": "add_archive_attempts",
        "sql_statements": MIGRATION_U4567890STUV_SQL,
    },
    {
        "id": "v5678901uvwx",
        "name": "add_source_expired",
        "sql_statements": MIGRATION_V5678901UVWX_SQL,
    },
    {
        "id": "5d2aef44594e",
        "name": "add_model_id_to_analyses",
        "sql_statements": MIGRATION_5D2AEF44594E_SQL,
    },
    {
        "id": "w6789012wxyz",
        "name": "add_carrier_api_support",
        "sql_statements": MIGRATION_W6789012WXYZ_SQL,
    },
    {
        "id": "x7890123abcd",
        "name": "phone_e164_constraint",
        "sql_statements": MIGRATION_X7890123ABCD_SQL,
    },
    {
        "id": "d3b3c3c4dd80",
        "name": "backfill_tracking_active_for_in_transit_books",
        "sql_statements": MIGRATION_D3B3C3C4DD80_SQL,
    },
    {
        "id": "7a6d67bc123e",
        "name": "change_analysis_job_model_default_to_opus",
        "sql_statements": MIGRATION_7A6D67BC123E_SQL,
    },
    {
        "id": "3c8716c1ec04",
        "name": "add_publisher_aliases_table",
        "sql_statements": MIGRATION_3C8716C1EC04_SQL,
    },
    {
        "id": "44275552664d",
        "name": "normalize_condition_grade",
        "sql_statements": MIGRATION_44275552664D_SQL,
    },
    {
        "id": "57f0cff7af60",
        "name": "add_unique_active_job_constraints",
        "sql_statements": MIGRATION_57F0CFF7AF60_SQL,
    },
    {
        "id": "dd7f743834bc",
        "name": "rerun_condition_grade_normalization",
        "sql_statements": MIGRATION_DD7F743834BC_SQL,
    },
    {
        "id": "21eb898ba04b",
        "name": "add_missing_condition_grade_mappings",
        "sql_statements": MIGRATION_21EB898BA04B_SQL,
    },
    {
        "id": "88779697decb",
        "name": "backfill_roi_pct",
        "sql_statements": MIGRATION_88779697DECB_SQL,
    },
    {
        "id": "y8901234bcde",
        "name": "add_unique_constraint_to_author_name",
        "sql_statements": MIGRATION_Y8901234BCDE_SQL,
    },
    {
        "id": "5bd4bb0308b4",
        "name": "normalize_condition_grade_casing",
        "sql_statements": MIGRATION_5BD4BB0308B4_SQL,
    },
    {
        "id": "z0012345cdef",
        "name": "add_cleanup_jobs_table",
        "sql_statements": MIGRATION_Z0012345CDEF_SQL,
    },
    {
        "id": "a1f2e3d4c5b6",
        "name": "add_failed_count_to_cleanup_jobs",
        "sql_statements": MIGRATION_Z1012345EFGH_SQL,
    },
    {
        "id": "b2c3d4e5f6a7",
        "name": "add_binder_operation_years",
        "sql_statements": MIGRATION_Z2012345GHIJ_SQL,
    },
    {
        "id": "c3d4e5f6g7h8",
        "name": "add_is_background_processed_to_book_images",
        "sql_statements": MIGRATION_C3D4E5F6G7H8_SQL,
    },
    {
        "id": "d4e5f6g7h8i9",
        "name": "add_image_processing_jobs_table",
        "sql_statements": MIGRATION_D4E5F6G7H8I9_SQL,
    },
    {
        "id": "0fc4653fe40b",
        "name": "add_image_processing_indexes_and_fix_failure_reason",
        "sql_statements": MIGRATION_0FC4653FE40B_SQL,
    },
    {
        "id": "z1234567defg",
        "name": "add_queue_retry_count",
        "sql_statements": MIGRATION_Z1234567DEFG_SQL,
    },
    {
        "id": "z2345678ghij",
        "name": "add_fk_indexes_for_eager_loading",
        "sql_statements": MIGRATION_Z2345678GHIJ_SQL,
    },
    {
        "id": "e5f6g7h8i9j0",
        "name": "add_entity_profiles_table",
        "sql_statements": MIGRATION_E5F6G7H8I9J0_SQL,
    },
    {
        "id": "f6g7h8i9j0k1",
        "name": "add_timestamps_to_entity_profiles",
        "sql_statements": MIGRATION_F6G7H8I9J0K1_SQL,
    },
    {
        "id": "g7h8i9j0k1l2",
        "name": "add_relationship_stories_to_entity_profiles",
        "sql_statements": MIGRATION_G7H8I9J0K1L2_SQL,
    },
    {
        "id": "h8i9j0k1l2m3",
        "name": "add_profile_generation_jobs",
        "sql_statements": MIGRATION_H8I9J0K1L2M3_SQL,
    },
    {
        "id": "z3456789ijkl",
        "name": "add_image_url_to_entity_tables",
        "sql_statements": MIGRATION_Z3456789IJKL_SQL,
    },
    {
        "id": "184855af397c",
        "name": "narrow_entity_profile_unique_constraint",
        "sql_statements": MIGRATION_184855AF397C_SQL,
    },
    {
        "id": "f7624c3b4e76",
        "name": "drop_entity_profile_owner_id",
        "sql_statements": MIGRATION_F7624C3B4E76_SQL,
    },
    {
        "id": "708c5a15f5bb",
        "name": "add_app_config_table",
        "sql_statements": MIGRATION_708C5A15F5BB_SQL,
    },
    {
        "id": "z4567890klmn",
        "name": "consolidate_config_tables",
        "sql_statements": MIGRATION_Z4567890KLMN_SQL,
    },
    {
        "id": "e9a5101c8557",
        "name": "add_ai_connections_column",
        "sql_statements": MIGRATION_E9A5101C8557_SQL,
    },
    {
        "id": "2843f260f764",
        "name": "add_ai_connections_table",
        "sql_statements": MIGRATION_2843F260F764_SQL,
    },
    {
        "id": "7a3a9a604ccf",
        "name": "null_broken_portrait_image_urls",
        "sql_statements": MIGRATION_7A3A9A604CCF_SQL,
    },
    {
        "id": "b3c8d2e1f4a7",
        "name": "backfill_entity_founded_years",
        "sql_statements": MIGRATION_B3C8D2E1F4A7_SQL,
    },
]
