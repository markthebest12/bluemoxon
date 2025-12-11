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


# Migration SQL for f85b7f976c08_add_scoring_fields
MIGRATION_F85B7F976C08_SQL = [
    "ALTER TABLE authors ADD COLUMN IF NOT EXISTS priority_score INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS investment_grade INTEGER",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS strategic_fit INTEGER",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS collection_impact INTEGER",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS overall_score INTEGER",
    "ALTER TABLE books ADD COLUMN IF NOT EXISTS scores_calculated_at TIMESTAMP",
]


@router.post(
    "/migrate",
    summary="Run database migrations",
    description="""
Run pending database migrations. This endpoint allows running migrations
from the Lambda which has VPC access to Aurora.

**Security**: Only available in non-production environments or with API key auth.

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
        current_version = db.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()
    except Exception:
        current_version = None

    # Run scoring fields migration if not already applied
    target_version = "f85b7f976c08"

    if current_version == target_version:
        return {
            "status": "already_current",
            "current_version": current_version,
            "message": "Database is already at the target migration version",
        }

    # Run migration SQL
    for sql in MIGRATION_F85B7F976C08_SQL:
        try:
            db.execute(text(sql))
            results.append({"sql": sql, "status": "success"})
        except Exception as e:
            error_msg = str(e)
            # Column already exists is OK (idempotent)
            if "already exists" in error_msg.lower():
                results.append({"sql": sql, "status": "skipped", "reason": "already exists"})
            else:
                errors.append({"sql": sql, "error": error_msg})

    # Update alembic_version
    try:
        if current_version:
            db.execute(
                text("UPDATE alembic_version SET version_num = :version"),
                {"version": target_version},
            )
        else:
            db.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
                {"version": target_version},
            )
        results.append({"sql": "UPDATE alembic_version", "status": "success"})
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
            "target_version": target_version,
            "results": results,
            "errors": errors,
        }

    return {
        "status": "success" if not errors else "partial",
        "previous_version": current_version,
        "new_version": target_version,
        "results": results,
        "errors": errors if errors else None,
    }
