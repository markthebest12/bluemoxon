"""Deep health check endpoints for system monitoring and CI/CD validation."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

import boto3
import redis
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectTimeoutError,
    ReadTimeoutError,
)
from fastapi import APIRouter, Depends
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError
from redis.exceptions import TimeoutError as RedisTimeoutError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.config import get_lambda_environment, get_settings
from app.db import get_db
from app.db.migration_sql import (
    CLEANUP_ORPHANS_SQL,
    TABLES_WITH_SEQUENCES,
)
from app.db.migration_sql import (
    MIGRATIONS as migrations,
)
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
    start = time.monotonic()
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

        latency_ms = round((time.monotonic() - start) * 1000, 2)
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
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
            "schema_validated": False,
        }


def check_s3() -> dict[str, Any]:
    """Check S3 bucket accessibility."""
    start = time.monotonic()
    try:
        s3 = boto3.client("s3", region_name=settings.aws_region)

        # Check images bucket exists and is accessible
        s3.head_bucket(Bucket=settings.images_bucket)

        # List a few objects to verify read access
        response = s3.list_objects_v2(
            Bucket=settings.images_bucket,
            MaxKeys=1,
        )

        latency_ms = round((time.monotonic() - start) * 1000, 2)
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
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "bucket": settings.images_bucket,
            "error": str(e),
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
        }


def check_cognito() -> dict[str, Any]:
    """Check Cognito user pool accessibility."""
    start = time.monotonic()

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
        latency_ms = round((time.monotonic() - start) * 1000, 2)

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
                "latency_ms": round((time.monotonic() - start) * 1000, 2),
            }
        # InvalidParameterException happens when using cross-account Cognito
        # (staging Lambda using prod Cognito via VPC endpoint routes to wrong account)
        # JWT validation still works via public JWKS endpoint, so auth functions
        if error_code == "InvalidParameterException":
            return {
                "status": "skipped",
                "reason": "Cross-account Cognito (expected in staging)",
                "latency_ms": round((time.monotonic() - start) * 1000, 2),
            }
        return {
            "status": "unhealthy",
            "error": error_code,
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
        }


def check_sqs() -> dict[str, Any]:
    """Check SQS queue accessibility for all configured queues."""
    start = time.monotonic()

    queues = {
        "analysis": settings.analysis_queue_name,
        "eval_runbook": settings.eval_runbook_queue_name,
        "image_processing": settings.image_processing_queue_name,
    }

    # Filter to only configured queues
    configured_queues = {k: v for k, v in queues.items() if v}

    if not configured_queues:
        return {
            "status": "skipped",
            "reason": "No SQS queues configured",
        }

    try:
        sqs = boto3.client("sqs", region_name=settings.aws_region)
        results = {}

        for queue_type, queue_name in configured_queues.items():
            try:
                # Get queue URL from name
                response = sqs.get_queue_url(QueueName=queue_name)
                queue_url = response["QueueUrl"]

                # Get queue attributes to verify access
                attrs = sqs.get_queue_attributes(
                    QueueUrl=queue_url,
                    AttributeNames=["ApproximateNumberOfMessages"],
                )
                msg_count = int(attrs["Attributes"].get("ApproximateNumberOfMessages", 0))

                results[queue_type] = {
                    "status": "healthy",
                    "queue_name": queue_name,
                    "messages": msg_count,
                }
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                results[queue_type] = {
                    "status": "unhealthy",
                    "queue_name": queue_name,
                    "error": error_code,
                }

        # Determine overall status
        statuses = [r["status"] for r in results.values()]
        if all(s == "healthy" for s in statuses):
            overall = "healthy"
        elif any(s == "unhealthy" for s in statuses):
            overall = "unhealthy"
        else:
            overall = "degraded"

        latency_ms = round((time.monotonic() - start) * 1000, 2)
        return {
            "status": overall,
            "queues": results,
            "latency_ms": latency_ms,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
        }


@lru_cache(maxsize=1)
def _get_bedrock_client():
    """Get or create a cached Bedrock client with timeouts configured.

    Uses lru_cache for thread-safe lazy initialization.
    """
    config = Config(connect_timeout=5, read_timeout=5)
    return boto3.client("bedrock", region_name=settings.aws_region, config=config)


@lru_cache(maxsize=1)
def _get_lambda_client():
    """Get or create cached Lambda client with timeout configuration.

    Uses lru_cache for thread-safe lazy initialization.
    """
    config = Config(connect_timeout=5, read_timeout=5)
    return boto3.client(
        "lambda",
        region_name=settings.aws_region,
        config=config,
    )


def _check_bedrock_sync() -> dict[str, Any]:
    """Check Bedrock service accessibility (sync version).

    Uses the Bedrock control plane API to list foundation models,
    which validates that the service is reachable and IAM permissions
    are configured.
    """
    start = time.monotonic()
    try:
        bedrock = _get_bedrock_client()

        # List foundation models to verify Bedrock access
        # This is a lightweight call that validates service connectivity
        bedrock.list_foundation_models(byOutputModality="TEXT")

        latency_ms = round((time.monotonic() - start) * 1000, 2)
        return {
            "status": "healthy",
            "latency_ms": latency_ms,
        }
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        # AccessDeniedException in production means IAM is broken - that's unhealthy
        # In dev/staging, permissions may not be configured, so skip
        if error_code == "AccessDeniedException":
            if settings.environment == "production":
                return {
                    "status": "unhealthy",
                    "error": "Bedrock IAM permissions not configured",
                    "latency_ms": latency_ms,
                }
            return {
                "status": "skipped",
                "reason": "IAM permissions not configured for Bedrock",
                "latency_ms": latency_ms,
            }
        return {
            "status": "unhealthy",
            "error": error_code,
            "latency_ms": latency_ms,
        }
    except (ConnectTimeoutError, ReadTimeoutError):
        return {
            "status": "unhealthy",
            "error": "Bedrock connection timeout",
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
        }
    except BotoCoreError:
        return {
            "status": "unhealthy",
            "error": "Bedrock SDK error",
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
        }


async def check_bedrock() -> dict[str, Any]:
    """Check Bedrock service accessibility (async wrapper).

    Uses run_in_executor to avoid blocking the async event loop
    during the synchronous boto3 API call.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _check_bedrock_sync)


def _check_single_lambda(
    lambda_client, function_name: str, service_key: str
) -> tuple[str, dict[str, Any]]:
    """Check a single Lambda function's availability.

    Args:
        lambda_client: The boto3 Lambda client to use.
        function_name: The full Lambda function name.
        service_key: The service key for result mapping.

    Returns:
        Tuple of (service_key, result_dict) for the Lambda check.
    """
    try:
        response = lambda_client.get_function(FunctionName=function_name)
        state = response["Configuration"]["State"]

        if state == "Active":
            return (
                service_key,
                {
                    "status": "healthy",
                    "function_name": function_name,
                    "state": state,
                },
            )
        elif state == "Failed":
            return (
                service_key,
                {
                    "status": "unhealthy",
                    "function_name": function_name,
                    "state": state,
                },
            )
        else:
            # Pending, Inactive states are degraded
            return (
                service_key,
                {
                    "status": "degraded",
                    "function_name": function_name,
                    "state": state,
                },
            )

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        if error_code == "ResourceNotFoundException":
            return (
                service_key,
                {
                    "status": "not_found",
                    "function_name": function_name,
                    "error": "Function not found",
                },
            )
        elif error_code == "AccessDeniedException":
            # AccessDeniedException in production means IAM is broken - that's unhealthy
            # In dev/staging, permissions may not be configured, so skip
            if settings.environment == "production":
                return (
                    service_key,
                    {
                        "status": "unhealthy",
                        "function_name": function_name,
                        "error": "Lambda IAM permissions not configured",
                    },
                )
            return (
                service_key,
                {
                    "status": "skipped",
                    "function_name": function_name,
                    "reason": "IAM permissions not configured for Lambda:GetFunction",
                },
            )
        else:
            return (
                service_key,
                {
                    "status": "error",
                    "function_name": function_name,
                    "error": error_code,
                },
            )
    except (ConnectTimeoutError, ReadTimeoutError) as e:
        return (
            service_key,
            {
                "status": "error",
                "function_name": function_name,
                "error": f"Timeout: {type(e).__name__}",
            },
        )
    except BotoCoreError as e:
        return (
            service_key,
            {
                "status": "error",
                "function_name": function_name,
                "error": str(e),
            },
        )


def _check_lambdas_sync() -> dict[str, Any]:
    """Check Lambda function availability (synchronous implementation).

    Checks the following Lambda functions in parallel:
    - bluemoxon-{env}-scraper - eBay listing scraping
    - bluemoxon-{env}-cleanup - Maintenance tasks
    - bluemoxon-{env}-image-processor - Background removal

    Returns:
        Dict with status (healthy/unhealthy/degraded/skipped), lambdas dict,
        and latency_ms.
    """
    start = time.monotonic()

    # Define Lambda functions to check
    # Each key is the health check identifier, value is the Lambda name suffix
    lambda_services = {
        "scraper": "scraper",
        "cleanup": "cleanup",
        "image_processor": "image-processor",
        "retry_queue_failed": "retry-queue-failed",
    }

    results = {}

    # Note: Assumes all Lambda functions use the same environment.
    # In a partial deploy scenario, individual functions could be in different states.
    env = get_lambda_environment("scraper")

    try:
        lambda_client = _get_lambda_client()

        # Check all Lambdas in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(
                    _check_single_lambda,
                    lambda_client,
                    f"bluemoxon-{env}-{name}",
                    key,
                ): key
                for key, name in lambda_services.items()
            }
            for future in as_completed(futures):
                key, result = future.result()
                results[key] = result

        # Determine overall status
        # Treat error and not_found as unhealthy since they indicate something is broken
        # Treat skipped as healthy (non-production environments without IAM permissions)
        statuses = [r["status"] for r in results.values()]
        if all(s in ("healthy", "skipped") for s in statuses):
            overall = "healthy"
        elif any(s in ("unhealthy", "error", "not_found") for s in statuses):
            overall = "unhealthy"
        else:
            overall = "degraded"

        latency_ms = round((time.monotonic() - start) * 1000, 2)
        return {
            "status": overall,
            "lambdas": results,
            "latency_ms": latency_ms,
        }

    except (ClientError, BotoCoreError, ConnectTimeoutError, ReadTimeoutError) as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
        }


async def check_lambdas() -> dict[str, Any]:
    """Check Lambda function availability (async wrapper).

    Wraps the synchronous Lambda check in run_in_executor to avoid
    blocking the async event loop.

    Returns:
        Dict with status (healthy/unhealthy/degraded/skipped), lambdas dict,
        and latency_ms.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _check_lambdas_sync)


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


def _check_redis_sync() -> dict[str, Any]:
    """Check Redis cache connectivity (sync version).

    Returns skipped status if redis_url is not configured (empty string).
    Uses PING command to verify connection.

    This is the internal sync implementation. Use check_redis() for the
    async wrapper that runs this in an executor to avoid blocking.
    """
    if not settings.redis_url:
        return {
            "status": "skipped",
            "reason": "Redis not configured",
        }

    start = time.monotonic()
    client = None
    try:
        client = redis.from_url(settings.redis_url, socket_timeout=5)
        client.ping()

        latency_ms = round((time.monotonic() - start) * 1000, 2)
        return {
            "status": "healthy",
            "latency_ms": latency_ms,
        }
    except RedisConnectionError:
        return {
            "status": "unhealthy",
            "error": "Redis connection failed",
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
        }
    except RedisTimeoutError:
        return {
            "status": "unhealthy",
            "error": "Redis connection timed out",
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
        }
    except RedisError:
        return {
            "status": "unhealthy",
            "error": "Redis error occurred",
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
        }
    finally:
        if client is not None:
            client.close()


async def check_redis() -> dict[str, Any]:
    """Check Redis cache connectivity (async wrapper).

    Returns skipped status if redis_url is not configured (empty string).
    Uses PING command to verify connection.

    Wraps _check_redis_sync in run_in_executor to avoid blocking the
    async event loop.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _check_redis_sync)


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
- **SQS**: Worker queue accessibility (analysis, eval_runbook, image_processing)
- **Cognito**: User pool availability (if configured)
- **Bedrock**: AI model service availability
- **Redis**: Cache connectivity (if configured)
- **Lambdas**: Lambda function availability (scraper, cleanup, image-processor, retry-queue-failed)
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
    start = time.monotonic()

    # Run async checks in parallel for better latency
    bedrock_result, lambdas_result, redis_result = await asyncio.gather(
        check_bedrock(),
        check_lambdas(),
        check_redis(),
    )

    # Sync checks run sequentially (they're fast and some share db session)
    checks = {
        "database": check_database(db),
        "s3": check_s3(),
        "sqs": check_sqs(),
        "cognito": check_cognito(),
        "bedrock": bedrock_result,
        "redis": redis_result,
        "lambdas": lambdas_result,
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

    total_latency = round((time.monotonic() - start) * 1000, 2)

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
async def cleanup_orphans(
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
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
async def recalculate_discounts(
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
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
async def merge_binders(
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """Merge duplicate binders to canonical names."""
    from app.models.binder import Binder
    from app.services.reference import normalize_binder_name

    results = []
    errors = []

    # Get all binders
    all_binders = db.query(Binder).all()

    # Group by canonical name
    canonical_map: dict[str, list[tuple[Binder, str | None]]] = {}
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
30. 21eb898ba04b - Add missing condition_grade mappings (G+, G-, NF-, F-, Good-, VGC)
31. 5bd4bb0308b4 - Normalize condition_grade values to UPPERCASE

Returns the list of SQL statements executed and their results.
    """,
    response_description="Migration results",
    tags=["health"],
)
async def run_migrations(
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """Run database migrations from Lambda (has VPC access to Aurora)."""
    results = []
    errors = []

    # Check current alembic version
    try:
        current_version = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:
        current_version = None

    # Use the migrations list imported from migration_sql module
    # Final version is the last migration in the list
    final_version = migrations[-1]["id"]

    # Always run all migrations - they are idempotent (IF NOT EXISTS)
    # This handles cases where alembic_version was updated but columns are missing
    for migration in migrations:
        version = migration["id"]
        sql_list = migration["sql_statements"]
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
                            {
                                "sql": sql,
                                "status": "skipped",
                                "reason": "already exists",
                            }
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
