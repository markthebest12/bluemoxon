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
    """Check database connectivity and basic queries."""
    start = time.time()
    try:
        # Test connection with simple query
        db.execute(text("SELECT 1"))

        # Test ORM query
        book_count = db.query(Book).count()

        latency_ms = round((time.time() - start) * 1000, 2)
        return {
            "status": "healthy",
            "latency_ms": latency_ms,
            "book_count": book_count,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round((time.time() - start) * 1000, 2),
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

    if not settings.database_url and not settings.database_secret_arn:
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


# Tables with auto-increment sequences for g7890123def0_fix_sequence_sync
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
    ]

    final_version = "i0123456abcd"

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
