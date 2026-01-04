"""Deep health check endpoints for system monitoring and CI/CD validation."""

import time
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Book
from app.version import get_version, get_version_info

router = APIRouter()
settings = get_settings()
app_version = get_version()


def check_database(db: Session) -> dict[str, Any]:
    """Check database connectivity and schema compatibility.

    This function validates that we can actually SELECT row data, not just
    COUNT(*). This catches schema mismatches (e.g., model has column X but
    database doesn't) that would cause API endpoints to fail with 500 errors
    while health check falsely reports healthy.
    """
    start = time.time()
    try:
        # Test connection with simple query
        db.execute(text("SELECT 1"))

        # Test ORM query - fetch actual row to validate schema compatibility
        # COUNT(*) alone doesn't access column data, so it won't catch missing columns
        first_book = db.query(Book).limit(1).first()
        schema_validated = first_book is not None or True  # True even if no books exist

        # If we got here without exception, schema is compatible
        # (SQLAlchemy would raise if model columns don't exist in DB)
        book_count = db.query(Book).count()

        latency_ms = round((time.time() - start) * 1000, 2)
        return {
            "status": "healthy",
            "latency_ms": latency_ms,
            "book_count": book_count,
            "schema_validated": schema_validated,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round((time.time() - start) * 1000, 2),
            "schema_validated": False,
        }


def check_s3() -> dict[str, Any]:
    """Check S3 bucket accessibility."""
    start = time.time()
    try:
        s3 = boto3.client("s3", region_name=settings.aws_region)

        # Check images bucket exists and is accessible
        s3.head_bucket(Bucket=settings.images_bucket)

        # List a few objects to verify read access
        response = s3.list_objects_v2(
            Bucket=settings.images_bucket,
            MaxKeys=1,
        )

        latency_ms = round((time.time() - start) * 1000, 2)
        return {
            "status": "healthy",
            "bucket": settings.images_bucket,
            "latency_ms": latency_ms,
            "has_objects": response.get("KeyCount", 0) > 0,
        }
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        return {
            "status": "unhealthy",
            "bucket": settings.images_bucket,
            "error": error_code,
            "latency_ms": round((time.time() - start) * 1000, 2),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "bucket": settings.images_bucket,
            "error": str(e),
            "latency_ms": round((time.time() - start) * 1000, 2),
        }


def check_cognito() -> dict[str, Any]:
    """Check Cognito user pool accessibility."""
    start = time.time()

    if not settings.cognito_user_pool_id:
        return {
            "status": "skipped",
            "reason": "cognito_user_pool_id not configured",
        }

    try:
        cognito = boto3.client("cognito-idp", region_name=settings.aws_region)

        # Describe user pool to verify access
        response = cognito.describe_user_pool(UserPoolId=settings.cognito_user_pool_id)

        pool_name = response["UserPool"]["Name"]
        latency_ms = round((time.time() - start) * 1000, 2)

        return {
            "status": "healthy",
            "user_pool": pool_name,
            "latency_ms": latency_ms,
        }
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        # AccessDeniedException is an IAM issue, not a service health issue
        if error_code == "AccessDeniedException":
            return {
                "status": "skipped",
                "reason": "IAM permissions not configured for Cognito describe",
                "latency_ms": round((time.time() - start) * 1000, 2),
            }
        # InvalidParameterException happens when using cross-account Cognito
        # (staging Lambda using prod Cognito via VPC endpoint routes to wrong account)
        # JWT validation still works via public JWKS endpoint, so auth functions
        if error_code == "InvalidParameterException":
            return {
                "status": "skipped",
                "reason": "Cross-account Cognito (expected in staging)",
                "latency_ms": round((time.time() - start) * 1000, 2),
            }
        return {
            "status": "unhealthy",
            "error": error_code,
            "latency_ms": round((time.time() - start) * 1000, 2),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round((time.time() - start) * 1000, 2),
        }


def check_config() -> dict[str, Any]:
    """Validate critical configuration is present."""
    issues = []

    if (
        not settings.database_url
        and not settings.database_secret_arn
        and not settings.database_secret_name
    ):
        issues.append("No database configuration")

    if not settings.images_bucket:
        issues.append("images_bucket not configured")

    if settings.environment == "production":
        if not settings.cognito_user_pool_id:
            issues.append("cognito_user_pool_id required in production")
        if not settings.cognito_app_client_id:
            issues.append("cognito_app_client_id required in production")
        if settings.cors_origins == "*":
            issues.append("CORS should not be wildcard in production")

    return {
        "status": "healthy" if not issues else "warning",
        "environment": settings.environment,
        "debug": settings.debug,
        "issues": issues if issues else None,
    }


@router.get(
    "/live",
    summary="Liveness probe",
    description="Simple check that the service is running. Use for Kubernetes liveness probes.",
    response_description="Returns ok if the service is alive",
    tags=["health"],
)
async def liveness():
    """Liveness probe - just checks if the service is running."""
    return {"status": "ok"}


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Checks if the service is ready to accept traffic. Validates database connectivity.",
    response_description="Returns ready status and database check result",
    tags=["health"],
)
async def readiness(db: Session = Depends(get_db)):
    """Readiness probe - checks if service can handle requests."""
    db_check = check_database(db)

    is_ready = db_check["status"] == "healthy"

    return {
        "status": "ready" if is_ready else "not_ready",
        "checks": {
            "database": db_check,
        },
    }


@router.get(
    "/deep",
    summary="Deep health check",
    description="""
Comprehensive health check that validates all system dependencies:
- **Database**: PostgreSQL connectivity and query execution
- **S3**: Images bucket accessibility
- **Cognito**: User pool availability (if configured)
- **Config**: Critical configuration validation

Use this endpoint for:
- CI/CD deployment validation
- Monitoring dashboards
- Troubleshooting connectivity issues

Returns detailed status for each component with latency measurements.
    """,
    response_description="Detailed health status of all system components",
    tags=["health"],
)
async def deep_health_check(db: Session = Depends(get_db)):
    """Deep health check - validates all dependencies."""
    start = time.time()

    # Run all checks
    checks = {
        "database": check_database(db),
        "s3": check_s3(),
        "cognito": check_cognito(),
        "config": check_config(),
    }

    # Determine overall status
    statuses = [c["status"] for c in checks.values()]
    if all(s in ("healthy", "skipped") for s in statuses):
        overall = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall = "unhealthy"
    else:
        overall = "degraded"

    total_latency = round((time.time() - start) * 1000, 2)

    return {
        "status": overall,
        "timestamp": datetime.now(UTC).isoformat(),
        "version": app_version,
        "environment": settings.environment,
        "total_latency_ms": total_latency,
        "checks": checks,
    }


@router.get(
    "/info",
    summary="Service information",
    description="Returns service metadata, version, and configuration summary.",
    response_description="Service information and configuration",
    tags=["health"],
)
async def service_info():
    """Service information endpoint."""
    version_info = get_version_info()
    return {
        "service": "bluemoxon-api",
        **version_info,
        "region": settings.aws_region,
        "features": {
            "cognito_auth": bool(settings.cognito_user_pool_id),
            "s3_images": bool(settings.images_bucket),
            "api_key_auth": bool(settings.api_key),
        },
        "endpoints": {
            "docs": "/docs" if settings.debug else None,
            "redoc": "/redoc" if settings.debug else None,
            "health": "/health",
            "api": "/api/v1",
        },
    }


@router.get(
    "/version",
    summary="Application version",
    description="Returns detailed version information including git SHA and deployment timestamp.",
    response_description="Version details",
    tags=["health"],
)
async def version():
    """Get application version details."""
    return get_version_info()


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
        WHERE name IN ('Zaehnsdorf', 'Rivière & Son', 'Riviere', 'Sangorski & Sutcliffe',
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

# Migration SQL for s2345678klmn_expand_binding_type
MIGRATION_S2345678KLMN_SQL = [
    "ALTER TABLE books ALTER COLUMN binding_type TYPE VARCHAR(100)",
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

# Migration SQL for s2345678klmn_add_author_tier (column)
MIGRATION_S2345678KLMN_AUTHOR_TIER_SQL = [
    "ALTER TABLE authors ADD COLUMN IF NOT EXISTS tier VARCHAR(10)",
]

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


@router.post(
    "/cleanup-orphans",
    summary="Clean up orphaned database records",
    description="""
Delete orphaned records where book_id references a non-existent book.
This can happen when CASCADE deletes fail or after database migrations.

Cleans up:
- book_analyses
- eval_runbooks
- book_images
- analysis_jobs
- eval_runbook_jobs

Returns count of deleted records from each table.
    """,
    response_description="Cleanup results",
    tags=["health"],
)
async def cleanup_orphans(db: Session = Depends(get_db)):
    """Clean up orphaned database records that reference non-existent books."""
    results = []
    errors = []
    total_deleted = 0

    for sql in CLEANUP_ORPHANS_SQL:
        try:
            result = db.execute(text(sql))
            rows_deleted = result.rowcount
            total_deleted += rows_deleted
            # Extract table name from SQL for reporting
            table_name = sql.split("FROM ")[1].split()[0]
            results.append({"table": table_name, "deleted": rows_deleted, "status": "success"})
        except Exception as e:
            errors.append({"sql": sql[:50] + "...", "error": str(e)})

    try:
        db.commit()
    except Exception as e:
        errors.append({"operation": "COMMIT", "error": str(e)})
        return {
            "status": "failed",
            "results": results,
            "errors": errors,
        }

    return {
        "status": "success" if not errors else "partial",
        "total_deleted": total_deleted,
        "results": results,
        "errors": errors if errors else None,
    }


@router.post(
    "/migrate",
    summary="Run database migrations",
    description="""
Run pending database migrations. This endpoint allows running migrations
from the Lambda which has VPC access to Aurora.

Migrations run in order:
1. e44df6ab5669 - Add acquisition columns (source_url, source_item_id, etc.)
2. f85b7f976c08 - Add scoring fields
3. g7890123def0 - Fix sequence sync (resets sequences to max(id) + 1)
4. h8901234efgh - Add is_complete field for multi-volume sets
5. i9012345abcd - Add archive fields (source_archived_url, archive_status)
6. 9d7720474d6d - Add admin_config table for currency rates
7. a1234567bcde - Add analysis_jobs table for async Bedrock analysis
8. i0123456abcd - Add binder tier column for scoring calculations
9. j2345678efgh - Add tracking fields (tracking_number, carrier, url)
10. k3456789ijkl - Add ship_date and estimated_delivery_end fields
11. l4567890mnop - Add acquisition_cost field for total cost tracking
12. m5678901qrst - Add eval_runbooks and eval_price_history tables
13. n6789012uvwx - Add eval_runbook_jobs table for async eval runbook generation
14. o7890123wxyz - Add fmv_notes and fmv_confidence to eval_runbooks
15. p8901234yzab - Add tracking_status and tracking_last_checked fields
16. q0123456cdef - Add provenance and first edition fields (is_first_edition, has_provenance, provenance_tier)
17. r1234567ghij - Add extraction_status field to book_analyses
18. s2345678klmn - Expand binding_type column to varchar(100)
19. t3456789lmno - Expand binders.name column to varchar(100)
20. 6e90a0c87832 - Add tiered recommendation fields to eval_runbooks
21. s2345678klmn - Add author tier column
22. f4f2fbe81faa - Seed author/publisher/binder tier values
23. t3456789opqr - Add preferred boolean to authors, publishers, binders
24. u4567890stuv - Add archive_attempts counter for retry tracking
25. v5678901uvwx - Add source_expired boolean for expired source URLs
26. 5d2aef44594e - Add model_id column to book_analyses for AI model tracking
27. w6789012wxyz - Add carrier API support (tracking_active, notifications table)
28. x7890123abcd - Add E.164 phone constraint and carrier_circuit_state table
29. d3b3c3c4dd80 - Backfill tracking_active for existing in-transit books

Returns the list of SQL statements executed and their results.
    """,
    response_description="Migration results",
    tags=["health"],
)
async def run_migrations(db: Session = Depends(get_db)):
    """Run database migrations from Lambda (has VPC access to Aurora)."""
    results = []
    errors = []

    # Check current alembic version
    try:
        current_version = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:
        current_version = None

    # Define migration chain - run all migrations regardless of version
    # Each migration uses IF NOT EXISTS/IF EXISTS to be idempotent
    migrations = [
        ("e44df6ab5669", MIGRATION_E44DF6AB5669_SQL),
        ("f85b7f976c08", MIGRATION_F85B7F976C08_SQL),
        ("g7890123def0", None),  # Sequence sync uses dynamic SQL
        ("h8901234efgh", MIGRATION_H8901234EFGH_SQL),
        ("i9012345abcd", MIGRATION_I9012345ABCD_SQL),
        ("9d7720474d6d", MIGRATION_9D7720474D6D_SQL),
        ("a1234567bcde", MIGRATION_A1234567BCDE_SQL),
        ("i0123456abcd", MIGRATION_I0123456ABCD_SQL),
        ("j2345678efgh", MIGRATION_J2345678EFGH_SQL),
        ("k3456789ijkl", MIGRATION_K3456789IJKL_SQL),
        ("l4567890mnop", MIGRATION_L4567890MNOP_SQL),
        ("m5678901qrst", MIGRATION_M5678901QRST_SQL),
        ("n6789012uvwx", MIGRATION_N6789012UVWX_SQL),
        ("o7890123wxyz", MIGRATION_O7890123WXYZ_SQL),
        ("p8901234yzab", MIGRATION_P8901234YZAB_SQL),
        ("q0123456cdef", MIGRATION_Q0123456CDEF_SQL),
        ("r1234567ghij", MIGRATION_R1234567GHIJ_SQL),
        ("s2345678klmn", MIGRATION_S2345678KLMN_SQL),
        ("t3456789lmno", MIGRATION_T3456789LMNO_SQL),
        ("6e90a0c87832", MIGRATION_6E90A0C87832_SQL),
        ("s2345678klmn", MIGRATION_S2345678KLMN_AUTHOR_TIER_SQL),
        ("f4f2fbe81faa", MIGRATION_F4F2FBE81FAA_SEED_TIERS_SQL),
        ("t3456789opqr", MIGRATION_T3456789OPQR_SQL),
        ("u4567890stuv", MIGRATION_U4567890STUV_SQL),
        ("v5678901uvwx", MIGRATION_V5678901UVWX_SQL),
        ("5d2aef44594e", MIGRATION_5D2AEF44594E_SQL),
        ("w6789012wxyz", MIGRATION_W6789012WXYZ_SQL),
        ("x7890123abcd", MIGRATION_X7890123ABCD_SQL),
        ("d3b3c3c4dd80", MIGRATION_D3B3C3C4DD80_SQL),
        ("7a6d67bc123e", MIGRATION_7A6D67BC123E_SQL),
    ]

    final_version = "7a6d67bc123e"

    # Always run all migrations - they are idempotent (IF NOT EXISTS)
    # This handles cases where alembic_version was updated but columns are missing
    for version, sql_list in migrations:
        if sql_list:
            # Run static SQL migrations
            for sql in sql_list:
                try:
                    db.execute(text(sql))
                    results.append({"sql": sql, "status": "success"})
                except Exception as e:
                    error_msg = str(e)
                    if "already exists" in error_msg.lower():
                        results.append(
                            {"sql": sql, "status": "skipped", "reason": "already exists"}
                        )
                    else:
                        errors.append({"sql": sql, "error": error_msg})
        elif version == "g7890123def0":
            # Run sequence sync migration
            # Table names are from hardcoded constant TABLES_WITH_SEQUENCES, not user input
            for table in TABLES_WITH_SEQUENCES:
                sql = f"""
                    SELECT setval(
                        pg_get_serial_sequence('{table}', 'id'),
                        COALESCE((SELECT MAX(id) FROM {table}), 0) + 1,
                        false
                    )
                """  # noqa: S608  # nosec B608
                try:
                    # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text
                    db.execute(text(sql))
                    results.append({"sql": f"setval({table}_id_seq)", "status": "success"})
                except Exception as e:
                    errors.append({"sql": f"setval({table}_id_seq)", "error": str(e)})

    # Update alembic_version to final version
    try:
        if current_version:
            db.execute(
                text("UPDATE alembic_version SET version_num = :version"),
                {"version": final_version},
            )
        else:
            db.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
                {"version": final_version},
            )
        results.append({"sql": f"UPDATE alembic_version to {final_version}", "status": "success"})
    except Exception as e:
        errors.append({"sql": "UPDATE alembic_version", "error": str(e)})

    # Commit the transaction
    try:
        db.commit()
    except Exception as e:
        errors.append({"sql": "COMMIT", "error": str(e)})
        return {
            "status": "failed",
            "previous_version": current_version,
            "target_version": final_version,
            "results": results,
            "errors": errors,
        }

    return {
        "status": "success" if not errors else "partial",
        "previous_version": current_version,
        "new_version": final_version,
        "results": results,
        "errors": errors if errors else None,
    }
