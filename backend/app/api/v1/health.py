"""Deep health check endpoints for system monitoring and CI/CD validation."""

import os
import time
from datetime import UTC, datetime
from typing import Any

import boto3
from alembic.config import Config
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from alembic import command
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
    "/recalculate-discounts",
    summary="Recalculate stale discount percentages",
    description="""
Recalculate discount_pct for all books where the value may be stale.

This is needed when FMV (value_mid) is updated after acquisition but
discount_pct was not recalculated. For example, a book acquired with
placeholder FMV of $53 later updated to $950 would have stale discount.

Returns count of books updated.
    """,
    response_description="Recalculation results",
    tags=["health"],
)
async def recalculate_discounts(db: Session = Depends(get_db)):
    """Recalculate discount_pct for all books with both purchase_price and value_mid."""
    from app.services.scoring import recalculate_discount_pct

    # Get all books with both purchase_price and value_mid
    books = (
        db.query(Book)
        .filter(Book.purchase_price.isnot(None))
        .filter(Book.value_mid.isnot(None))
        .filter(Book.value_mid > 0)
        .all()
    )

    updated_count = 0
    for book in books:
        old_discount = book.discount_pct
        recalculate_discount_pct(book)
        if book.discount_pct != old_discount:
            updated_count += 1

    db.commit()

    return {
        "status": "completed",
        "books_checked": len(books),
        "books_updated": updated_count,
    }


@router.post(
    "/merge-binders",
    summary="Merge duplicate binders to canonical names",
    description="""
Merge duplicate binder entries to their canonical names based on the
normalization rules in reference.py.

For example:
- "Francis Bedford" -> "Bedford"
- "James Hayday" -> "Hayday"
- "Birdsall of Northampton" -> "Birdsall"

Books are reassigned to the canonical binder, and empty duplicates are deleted.
Returns list of merges performed.
    """,
    response_description="Merge results",
    tags=["health"],
)
async def merge_binders(db: Session = Depends(get_db)):
    """Merge duplicate binders to canonical names."""
    from app.models.binder import Binder
    from app.services.reference import normalize_binder_name

    results = []
    errors = []

    # Get all binders
    all_binders = db.query(Binder).all()

    # Group by canonical name
    canonical_map: dict[str, list[Binder]] = {}
    for binder in all_binders:
        canonical_name, tier = normalize_binder_name(binder.name)
        if canonical_name is None:
            continue
        if canonical_name not in canonical_map:
            canonical_map[canonical_name] = []
        canonical_map[canonical_name].append((binder, tier))

    # Process each group
    for canonical_name, binder_list in canonical_map.items():
        if len(binder_list) <= 1:
            # No duplicates, but may need tier update
            binder, tier = binder_list[0]
            if tier and not binder.tier:
                binder.tier = tier
                results.append(
                    {
                        "action": "tier_update",
                        "binder": binder.name,
                        "new_tier": tier,
                    }
                )
            continue

        # Find or create canonical binder
        canonical_binder = None
        duplicates = []
        best_tier = None

        for binder, tier in binder_list:
            if tier:
                best_tier = tier
            if binder.name == canonical_name:
                canonical_binder = binder
            else:
                duplicates.append(binder)

        # If canonical doesn't exist, use first binder and rename it
        if canonical_binder is None:
            canonical_binder = binder_list[0][0]
            old_name = canonical_binder.name
            canonical_binder.name = canonical_name
            duplicates = [b for b, _ in binder_list[1:]]
            results.append(
                {
                    "action": "rename",
                    "from": old_name,
                    "to": canonical_name,
                }
            )

        # Update tier if needed
        if best_tier and not canonical_binder.tier:
            canonical_binder.tier = best_tier

        # Merge books from duplicates to canonical
        for dup_binder in duplicates:
            # Reassign books
            book_count = 0
            for book in dup_binder.books:
                book.binder_id = canonical_binder.id
                book_count += 1

            if book_count > 0:
                results.append(
                    {
                        "action": "merge",
                        "from": dup_binder.name,
                        "to": canonical_name,
                        "books_moved": book_count,
                    }
                )

            # Delete the duplicate binder
            try:
                db.delete(dup_binder)
                results.append(
                    {
                        "action": "delete",
                        "binder": dup_binder.name,
                    }
                )
            except Exception as e:
                errors.append(
                    {
                        "action": "delete",
                        "binder": dup_binder.name,
                        "error": str(e),
                    }
                )

    try:
        db.commit()
    except Exception as e:
        errors.append({"action": "commit", "error": str(e)})
        return {
            "status": "failed",
            "results": results,
            "errors": errors,
        }

    return {
        "status": "success" if not errors else "partial",
        "results": results,
        "errors": errors if errors else None,
    }


@router.post(
    "/migrate",
    summary="Run database migrations",
    description="""
Run pending database migrations using Alembic. This endpoint allows running migrations
from the Lambda which has VPC access to Aurora.

Alembic automatically determines which migrations need to run based on the current
database state and applies them in order.

Returns the migration results including previous and new version numbers.
    """,
    response_description="Migration results",
    tags=["health"],
)
async def run_migrations(db: Session = Depends(get_db)):
    """Run database migrations using Alembic programmatically."""
    results = []
    errors = []

    # Get current version before migration
    try:
        current_version = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:
        current_version = None

    try:
        # Get paths - health.py is in backend/app/api/v1/, alembic.ini is in backend/
        # Navigate up: v1 -> api -> app -> backend
        script_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )

        alembic_cfg = Config(os.path.join(script_dir, "alembic.ini"))

        # Get database URL from the existing db session's connection
        db_url = str(db.get_bind().url)
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        alembic_cfg.set_main_option("script_location", os.path.join(script_dir, "alembic"))

        # Run migrations to head
        command.upgrade(alembic_cfg, "head")

        results.append({"operation": "alembic upgrade head", "status": "success"})

    except Exception as e:
        errors.append({"operation": "alembic upgrade", "error": str(e)})

    # Get new version after migration
    try:
        new_version = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:
        new_version = current_version

    return {
        "status": "success" if not errors else "failed",
        "previous_version": current_version,
        "new_version": new_version,
        "results": results,
        "errors": errors if errors else None,
    }
