"""Admin configuration API endpoints."""

import json
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

import boto3
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.health import check_cognito, check_database, check_s3, check_sqs
from app.auth import require_admin
from app.cold_start import get_cold_start_status
from app.config import get_cleanup_environment, get_settings
from app.db.session import get_db
from app.models.admin_config import AdminConfig
from app.models.author import Author
from app.models.binder import Binder
from app.models.cleanup_job import CleanupJob
from app.models.publisher import Publisher
from app.services import tiered_scoring
from app.services.bedrock import (
    CLAUDE_MAX_IMAGE_BYTES,
    CLAUDE_SAFE_RAW_BYTES,
    MODEL_IDS,
    MODEL_USAGE,
    PROMPT_CACHE_TTL,
)
from app.services.cost_explorer import get_costs as fetch_costs
from app.version import get_version_info
from lambdas.cleanup.handler import cleanup_stale_listings

router = APIRouter()


class ConfigResponse(BaseModel):
    """Admin config response."""

    gbp_to_usd_rate: float
    eur_to_usd_rate: float


class ConfigUpdate(BaseModel):
    """Admin config update request."""

    gbp_to_usd_rate: float | None = None
    eur_to_usd_rate: float | None = None


class HealthCheck(BaseModel):
    """Individual health check result."""

    status: str
    latency_ms: float | None = None
    error: str | None = None
    book_count: int | None = None
    bucket: str | None = None
    user_pool: str | None = None
    reason: str | None = None


class SqsQueueHealth(BaseModel):
    """Health check for a single SQS queue."""

    status: str
    queue_name: str
    messages: int | None = None
    error: str | None = None


class SqsHealthCheck(BaseModel):
    """SQS health check results."""

    status: str
    latency_ms: float | None = None
    reason: str | None = None
    error: str | None = None
    queues: dict[str, SqsQueueHealth] | None = None


class HealthChecks(BaseModel):
    """All health check results."""

    database: HealthCheck
    s3: HealthCheck
    cognito: HealthCheck
    sqs: SqsHealthCheck | None = None


class HealthInfo(BaseModel):
    """Health summary."""

    overall: str
    total_latency_ms: float
    checks: HealthChecks


class SystemInfo(BaseModel):
    """System version and deployment info."""

    version: str
    git_sha: str | None = None
    deploy_time: str | None = None
    environment: str


class EntityTier(BaseModel):
    """Entity with tier information."""

    name: str
    tier: str


class EntityTiers(BaseModel):
    """All tiered entities."""

    authors: list[EntityTier]
    publishers: list[EntityTier]
    binders: list[EntityTier]


class ModelInfo(BaseModel):
    """AI model information."""

    model_id: str
    usage: str


class InfrastructureConfig(BaseModel):
    """AWS infrastructure configuration."""

    aws_region: str
    images_bucket: str
    backup_bucket: str
    images_cdn_url: str | None = None
    analysis_queue: str | None = None
    eval_runbook_queue: str | None = None
    image_processing_queue: str | None = None


class LimitsConfig(BaseModel):
    """System limits and timeouts."""

    bedrock_read_timeout_sec: int
    bedrock_connect_timeout_sec: int
    image_max_bytes: int
    image_safe_bytes: int
    prompt_cache_ttl_sec: int
    presigned_url_expiry_sec: int


class BedrockModelCost(BaseModel):
    """Cost for a single Bedrock model."""

    model_name: str
    usage: str
    mtd_cost: float


class DailyCost(BaseModel):
    """Daily cost data point."""

    date: str
    cost: float


class CostResponse(BaseModel):
    """Cost data response."""

    period_start: str
    period_end: str
    bedrock_models: list[BedrockModelCost]
    bedrock_total: float
    daily_trend: list[DailyCost]
    other_costs: dict[str, float]
    total_aws_cost: float
    cached_at: str
    error: str | None = None


class SystemInfoResponse(BaseModel):
    """Complete system info response."""

    is_cold_start: bool
    timestamp: str
    system: SystemInfo
    health: HealthInfo
    models: dict[str, ModelInfo]
    infrastructure: InfrastructureConfig
    limits: LimitsConfig
    scoring_config: dict
    entity_tiers: EntityTiers


class CleanupRequest(BaseModel):
    """Cleanup operation request."""

    action: Literal["all", "stale", "expired", "orphans", "archives"] = "all"
    delete_orphans: bool = False


class CleanupResult(BaseModel):
    """Cleanup operation result."""

    stale_archived: int = 0
    sources_checked: int = 0
    sources_expired: int = 0
    orphans_found: int = 0
    orphans_deleted: int = 0
    archives_retried: int = 0
    archives_succeeded: int = 0
    archives_failed: int = 0


# New models for orphan scan and cleanup job tracking


class OrphanGroup(BaseModel):
    """A group of orphaned images for a specific book folder."""

    folder_id: int
    book_id: int | None
    book_title: str | None
    count: int
    bytes: int
    keys: list[str]


class OrphanScanResult(BaseModel):
    """Result of scanning for orphaned images."""

    total_count: int
    total_bytes: int
    orphans_by_book: list[OrphanGroup]


class DeleteJobRequest(BaseModel):
    """Request to start an orphan deletion job."""

    total_count: int
    total_bytes: int


class DeleteJobResponse(BaseModel):
    """Response when a deletion job is started."""

    job_id: UUID
    status: str


class CleanupJobStatus(BaseModel):
    """Status of a cleanup job."""

    job_id: UUID
    status: str
    progress_pct: float
    total_count: int
    total_bytes: int
    deleted_count: int
    deleted_bytes: int
    failed_count: int = 0
    error_message: str | None = None
    created_at: str
    completed_at: str | None = None


# Models for listings cleanup


class ListingGroup(BaseModel):
    """A group of stale listing images for a specific item."""

    item_id: str
    count: int
    bytes: int
    oldest: str


class ListingsScanResult(BaseModel):
    """Result of scanning for stale listing images."""

    total_count: int
    total_bytes: int
    age_threshold_days: int
    listings_by_item: list[ListingGroup]
    deleted_count: int = 0
    failed_count: int = 0
    truncated: bool = False


class ListingsDeleteRequest(BaseModel):
    """Request to delete stale listing images."""

    age_days: int = 30


def get_scoring_config() -> dict:
    """Collect all scoring constants from tiered_scoring module."""
    return {
        "quality_points": {
            "publisher_tier_1": tiered_scoring.QUALITY_TIER_1_PUBLISHER,
            "publisher_tier_2": tiered_scoring.QUALITY_TIER_2_PUBLISHER,
            "binder_tier_1": tiered_scoring.QUALITY_TIER_1_BINDER,
            "binder_tier_2": tiered_scoring.QUALITY_TIER_2_BINDER,
            "double_tier_1_bonus": tiered_scoring.QUALITY_DOUBLE_TIER_1_BONUS,
            "era_bonus": tiered_scoring.QUALITY_ERA_BONUS,
            "condition_fine": tiered_scoring.QUALITY_CONDITION_FINE,
            "condition_good": tiered_scoring.QUALITY_CONDITION_GOOD,
            "complete_set": tiered_scoring.QUALITY_COMPLETE_SET,
            "author_priority_cap": tiered_scoring.QUALITY_AUTHOR_PRIORITY_CAP,
            "duplicate_penalty": tiered_scoring.QUALITY_DUPLICATE_PENALTY,
            "large_volume_penalty": tiered_scoring.QUALITY_LARGE_VOLUME_PENALTY,
            "preferred_bonus": tiered_scoring.PREFERRED_BONUS,
        },
        "strategic_points": {
            "publisher_match": tiered_scoring.STRATEGIC_PUBLISHER_MATCH,
            "new_author": tiered_scoring.STRATEGIC_NEW_AUTHOR,
            "second_work": tiered_scoring.STRATEGIC_SECOND_WORK,
            "completes_set": tiered_scoring.STRATEGIC_COMPLETES_SET,
        },
        "thresholds": {
            "price_excellent": float(tiered_scoring.PRICE_EXCELLENT_THRESHOLD),
            "price_good": float(tiered_scoring.PRICE_GOOD_THRESHOLD),
            "price_fair": float(tiered_scoring.PRICE_FAIR_THRESHOLD),
            "strategic_floor": tiered_scoring.STRATEGIC_FIT_FLOOR,
            "quality_floor": tiered_scoring.QUALITY_FLOOR,
        },
        "weights": {
            "quality": tiered_scoring.QUALITY_WEIGHT,
            "strategic_fit": tiered_scoring.STRATEGIC_FIT_WEIGHT,
        },
        "offer_discounts": {
            "70-79": float(tiered_scoring.OFFER_DISCOUNTS[(70, 79)]),
            "60-69": float(tiered_scoring.OFFER_DISCOUNTS[(60, 69)]),
            "50-59": float(tiered_scoring.OFFER_DISCOUNTS[(50, 59)]),
            "40-49": float(tiered_scoring.OFFER_DISCOUNTS[(40, 49)]),
            "0-39": float(tiered_scoring.OFFER_DISCOUNTS[(0, 39)]),
            "strategic_floor": float(tiered_scoring.STRATEGIC_FLOOR_DISCOUNT),
            "quality_floor": float(tiered_scoring.QUALITY_FLOOR_DISCOUNT),
        },
        "era_boundaries": {
            "romantic_start": tiered_scoring.ROMANTIC_START,
            "romantic_end": tiered_scoring.ROMANTIC_END,
            "victorian_start": tiered_scoring.VICTORIAN_START,
            "victorian_end": tiered_scoring.VICTORIAN_END,
        },
    }


@router.get("/config", response_model=ConfigResponse)
def get_config(
    response: Response,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """Get admin configuration (admin only)."""
    response.headers["Cache-Control"] = "no-store"
    result = db.execute(select(AdminConfig))
    configs = {c.key: c.value for c in result.scalars().all()}
    return ConfigResponse(
        gbp_to_usd_rate=float(configs.get("gbp_to_usd_rate", 1.35)),
        eur_to_usd_rate=float(configs.get("eur_to_usd_rate", 1.17)),
    )


@router.put("/config", response_model=ConfigResponse)
def update_config(
    updates: ConfigUpdate,
    response: Response,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """Update admin configuration (admin only)."""
    for key, value in updates.model_dump(exclude_none=True).items():
        config = db.get(AdminConfig, key)
        if config:
            config.value = value
        else:
            db.add(AdminConfig(key=key, value=value))
    db.commit()
    return get_config(response, db)


@router.get("/system-info", response_model=SystemInfoResponse)
def get_system_info(
    response: Response,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """Get comprehensive system information for admin dashboard (admin only).

    Returns version info, health checks, infrastructure config,
    limits, scoring configuration, and tiered entities.
    """
    import time

    from app.config import get_settings

    response.headers["Cache-Control"] = "no-store"
    settings = get_settings()
    start = time.time()

    # Get cold start status
    is_cold_start = get_cold_start_status()

    # Get version info
    version_info = get_version_info()

    # Run health checks
    db_health = check_database(db)
    s3_health = check_s3()
    cognito_health = check_cognito()
    sqs_health = check_sqs()

    # Determine overall health
    statuses = [
        db_health["status"],
        s3_health["status"],
        cognito_health["status"],
        sqs_health["status"],
    ]
    if all(s in ("healthy", "skipped") for s in statuses):
        overall = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall = "unhealthy"
    else:
        overall = "degraded"

    total_latency = round((time.time() - start) * 1000, 2)

    # Get tiered entities
    authors = (
        db.query(Author)
        .filter(Author.tier.in_(["TIER_1", "TIER_2", "TIER_3"]))
        .order_by(Author.tier, Author.name)
        .all()
    )

    publishers = (
        db.query(Publisher)
        .filter(Publisher.tier.in_(["TIER_1", "TIER_2", "TIER_3"]))
        .order_by(Publisher.tier, Publisher.name)
        .all()
    )

    binders = (
        db.query(Binder)
        .filter(Binder.tier.in_(["TIER_1", "TIER_2", "TIER_3"]))
        .order_by(Binder.tier, Binder.name)
        .all()
    )

    return SystemInfoResponse(
        is_cold_start=is_cold_start,
        timestamp=datetime.now(UTC).isoformat(),
        system=SystemInfo(
            version=version_info.get("version", "unknown"),
            git_sha=version_info.get("git_sha"),
            deploy_time=version_info.get("deployed_at"),
            environment=version_info.get("environment", "unknown"),
        ),
        health=HealthInfo(
            overall=overall,
            total_latency_ms=total_latency,
            checks=HealthChecks(
                database=HealthCheck(**db_health),
                s3=HealthCheck(**s3_health),
                cognito=HealthCheck(**cognito_health),
                sqs=SqsHealthCheck(
                    status=sqs_health["status"],
                    latency_ms=sqs_health.get("latency_ms"),
                    reason=sqs_health.get("reason"),
                    error=sqs_health.get("error"),
                    queues={
                        k: SqsQueueHealth(**v)
                        for k, v in sqs_health.get("queues", {}).items()
                    }
                    if sqs_health.get("queues")
                    else None,
                ),
            ),
        ),
        models={
            name: ModelInfo(model_id=model_id, usage=MODEL_USAGE.get(name, ""))
            for name, model_id in MODEL_IDS.items()
        },
        infrastructure=InfrastructureConfig(
            aws_region=settings.aws_region,
            images_bucket=settings.images_bucket,
            backup_bucket=settings.backup_bucket,
            images_cdn_url=settings.images_cdn_url,
            analysis_queue=settings.analysis_queue_name,
            eval_runbook_queue=settings.eval_runbook_queue_name,
            image_processing_queue=settings.image_processing_queue_name,
        ),
        limits=LimitsConfig(
            bedrock_read_timeout_sec=540,
            bedrock_connect_timeout_sec=10,
            image_max_bytes=CLAUDE_MAX_IMAGE_BYTES,
            image_safe_bytes=CLAUDE_SAFE_RAW_BYTES,
            prompt_cache_ttl_sec=PROMPT_CACHE_TTL,
            presigned_url_expiry_sec=3600,
        ),
        scoring_config=get_scoring_config(),
        entity_tiers=EntityTiers(
            authors=[EntityTier(name=a.name, tier=a.tier) for a in authors],
            publishers=[EntityTier(name=p.name, tier=p.tier) for p in publishers],
            binders=[EntityTier(name=b.name, tier=b.tier) for b in binders],
        ),
    )


@router.get("/costs", response_model=CostResponse)
def get_costs(
    response: Response,
    timezone: str | None = Query(
        None,
        max_length=64,
        description="IANA timezone name (e.g., 'America/Los_Angeles') for MTD calculation",
    ),
    refresh: bool = False,
    _user=Depends(require_admin),
):
    """Get AWS cost data for admin dashboard (admin only).

    Args:
        timezone: Optional timezone for determining current month. If provided,
                  uses browser's local time to calculate MTD instead of UTC.
        refresh: If True, bypass server cache and fetch fresh data from AWS.

    Returns Bedrock model costs with usage descriptions,
    daily trend, and other AWS service costs.
    Cached server-side for 1 hour (see cost_explorer.py).
    """
    response.headers["Cache-Control"] = "no-store"
    return CostResponse(**fetch_costs(timezone=timezone, force_refresh=refresh))


def _invoke_cleanup_lambda(
    lambda_client, payload: dict, invocation_type: str = "RequestResponse"
) -> dict:
    """Invoke cleanup Lambda with fallback for deployment transitions.

    During deployment, the Lambda may be renamed (e.g., bluemoxon-production-cleanup
    to bluemoxon-prod-cleanup). This function tries the new name first, then falls
    back to the old name if not found.
    """
    settings = get_settings()
    new_name = f"bluemoxon-{get_cleanup_environment()}-cleanup"
    old_name = f"bluemoxon-{settings.environment}-cleanup"

    try:
        return lambda_client.invoke(
            FunctionName=new_name,
            InvocationType=invocation_type,
            Payload=json.dumps(payload),
        )
    except lambda_client.exceptions.ResourceNotFoundException:
        # Fallback to old name during deployment transition
        if new_name != old_name:
            return lambda_client.invoke(
                FunctionName=old_name,
                InvocationType=invocation_type,
                Payload=json.dumps(payload),
            )
        raise


@router.post("/cleanup", response_model=CleanupResult)
def run_cleanup(
    request: CleanupRequest,
    _user=Depends(require_admin),
):
    """Invoke cleanup Lambda to run maintenance tasks (admin only).

    Supports running individual or all cleanup operations:
    - stale: Archive books stuck in EVALUATING for 30+ days
    - expired: Check source URLs and mark expired ones
    - orphans: Find/delete orphaned S3 images
    - archives: Retry failed Wayback archives
    - all: Run all of the above
    """
    settings = get_settings()
    lambda_client = boto3.client("lambda", region_name=settings.aws_region)

    # Build payload for cleanup Lambda
    payload = {
        "action": request.action,
        "delete_orphans": request.delete_orphans,
        "bucket": settings.images_bucket,
    }

    # Invoke cleanup Lambda with fallback for deployment transitions
    response = _invoke_cleanup_lambda(lambda_client, payload)

    # Parse response
    result = json.loads(response["Payload"].read())

    # Check for Lambda error
    if "error" in result:
        raise HTTPException(status_code=500, detail=f"Cleanup error: {result['error']}")

    # Map Lambda response to CleanupResult
    return CleanupResult(
        stale_archived=result.get("stale_evaluations_archived", 0),
        sources_checked=result.get("sources_checked", 0),
        sources_expired=result.get("sources_expired", 0),
        orphans_found=result.get("orphans_found", 0),
        orphans_deleted=result.get("orphans_deleted", 0),
        archives_retried=result.get("archives_retried", 0),
        archives_succeeded=result.get("archives_succeeded", 0),
        archives_failed=result.get("archives_failed", 0),
    )


@router.get("/cleanup/orphans/scan", response_model=OrphanScanResult)
def scan_orphans(_user=Depends(require_admin)):
    """Scan for orphaned images with sizes.

    Invokes the cleanup Lambda with action='orphans' and delete_orphans=False
    to get a detailed report of orphaned images grouped by book folder.
    """
    settings = get_settings()
    lambda_client = boto3.client("lambda", region_name=settings.aws_region)

    # Build payload for cleanup Lambda
    payload = {
        "action": "orphans",
        "delete_orphans": False,
        "bucket": settings.images_bucket,
        "return_details": True,  # Request detailed orphan info
    }

    # Invoke cleanup Lambda with fallback for deployment transitions
    response = _invoke_cleanup_lambda(lambda_client, payload)

    # Parse response
    result = json.loads(response["Payload"].read())

    # Check for Lambda error
    if "error" in result:
        raise HTTPException(status_code=500, detail=f"Scan error: {result['error']}")

    # Map Lambda response to OrphanScanResult
    orphans_by_book = [
        OrphanGroup(
            folder_id=group.get("folder_id", 0),
            book_id=group.get("book_id"),
            book_title=group.get("book_title"),
            count=group.get("count", 0),
            bytes=group.get("bytes", 0),
            keys=group.get("keys", []),
        )
        for group in result.get("orphans_by_book", [])
    ]

    return OrphanScanResult(
        total_count=result.get("orphans_found", 0),
        total_bytes=result.get("total_bytes", 0),
        orphans_by_book=orphans_by_book,
    )


@router.post("/cleanup/orphans/delete", response_model=DeleteJobResponse, status_code=202)
def start_orphan_delete(
    request: DeleteJobRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """Start an orphan deletion job.

    Creates a CleanupJob record to track the deletion progress.
    The actual deletion is performed asynchronously by invoking
    the cleanup Lambda with the job_id.

    Returns 202 Accepted with job_id for status polling.
    Returns 409 Conflict if a job is already in progress.
    """
    # Check for existing in-progress job
    existing_job = db.execute(
        select(CleanupJob).where(CleanupJob.status.in_(["pending", "running"]))
    ).scalar_one_or_none()
    if existing_job:
        raise HTTPException(
            status_code=409,
            detail=f"A cleanup job is already in progress (job_id: {existing_job.id})",
        )

    job = CleanupJob(
        total_count=request.total_count,
        total_bytes=request.total_bytes,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Invoke Lambda asynchronously for background deletion
    settings = get_settings()
    lambda_client = boto3.client("lambda", region_name=settings.aws_region)

    payload = {
        "job_id": str(job.id),
        "bucket": settings.images_bucket,
    }
    _invoke_cleanup_lambda(lambda_client, payload, invocation_type="Event")

    return DeleteJobResponse(job_id=job.id, status=job.status)


@router.get("/cleanup/jobs/{job_id}", response_model=CleanupJobStatus)
def get_cleanup_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """Get the status of a cleanup job."""
    job = db.get(CleanupJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Detect timeout: pending job older than 5 minutes means Lambda failed to start
    if job.status == "pending":
        job_age = datetime.now(UTC) - job.created_at
        if job_age > timedelta(minutes=5):
            job.status = "failed"
            job.error_message = "Job timed out waiting to start (Lambda may have failed)"
            job.completed_at = datetime.now(UTC)
            db.commit()
            db.refresh(job)

    return CleanupJobStatus(
        job_id=job.id,
        status=job.status,
        progress_pct=job.progress_pct,
        total_count=job.total_count,
        total_bytes=job.total_bytes,
        deleted_count=job.deleted_count,
        deleted_bytes=job.deleted_bytes,
        failed_count=job.failed_count,
        error_message=job.error_message,
        created_at=job.created_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )


@router.get("/cleanup/listings/scan", response_model=ListingsScanResult)
def scan_stale_listings(
    age_days: int = 30,
    _user=Depends(require_admin),
):
    """Scan for stale listing images (dry run).

    Returns count and size of listings older than age_days threshold.
    Listings are temporary images scraped from eBay that haven't been
    imported into the book library.
    """
    from app.config import get_settings

    settings = get_settings()
    result = cleanup_stale_listings(bucket=settings.images_bucket, age_days=age_days, delete=False)

    # Map result to response model
    listings_by_item = [
        ListingGroup(
            item_id=item.get("item_id", ""),
            count=item.get("count", 0),
            bytes=item.get("bytes", 0),
            oldest=item.get("oldest", ""),
        )
        for item in result.get("listings_by_item", [])
    ]

    return ListingsScanResult(
        total_count=result.get("total_count", 0),
        total_bytes=result.get("total_bytes", 0),
        age_threshold_days=result.get("age_threshold_days", age_days),
        listings_by_item=listings_by_item,
        deleted_count=result.get("deleted_count", 0),
        failed_count=result.get("failed_count", 0),
        truncated=result.get("truncated", False),
    )


@router.post("/cleanup/listings/delete", response_model=ListingsScanResult)
def delete_stale_listings(
    request: ListingsDeleteRequest,
    _user=Depends(require_admin),
):
    """Delete stale listing images.

    Permanently removes listings older than age_days threshold.
    """
    from app.config import get_settings

    settings = get_settings()
    result = cleanup_stale_listings(
        bucket=settings.images_bucket, age_days=request.age_days, delete=True
    )

    # Map result to response model
    listings_by_item = [
        ListingGroup(
            item_id=item.get("item_id", ""),
            count=item.get("count", 0),
            bytes=item.get("bytes", 0),
            oldest=item.get("oldest", ""),
        )
        for item in result.get("listings_by_item", [])
    ]

    return ListingsScanResult(
        total_count=result.get("total_count", 0),
        total_bytes=result.get("total_bytes", 0),
        age_threshold_days=result.get("age_threshold_days", request.age_days),
        listings_by_item=listings_by_item,
        deleted_count=result.get("deleted_count", 0),
        failed_count=result.get("failed_count", 0),
        truncated=result.get("truncated", False),
    )
