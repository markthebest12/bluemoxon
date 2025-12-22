"""Admin configuration API endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.health import check_cognito, check_database, check_s3
from app.auth import require_admin
from app.cold_start import get_cold_start_status
from app.db.session import get_db
from app.models.admin_config import AdminConfig
from app.models.author import Author
from app.models.binder import Binder
from app.models.publisher import Publisher
from app.services import tiered_scoring
from app.services.bedrock import MODEL_IDS, MODEL_USAGE
from app.version import get_version_info

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


class HealthChecks(BaseModel):
    """All health check results."""

    database: HealthCheck
    s3: HealthCheck
    cognito: HealthCheck


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


class SystemInfoResponse(BaseModel):
    """Complete system info response."""

    is_cold_start: bool
    timestamp: str
    system: SystemInfo
    health: HealthInfo
    models: dict[str, ModelInfo]
    scoring_config: dict
    entity_tiers: EntityTiers


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
def get_config(db: Session = Depends(get_db)):
    """Get admin configuration."""
    result = db.execute(select(AdminConfig))
    configs = {c.key: c.value for c in result.scalars().all()}
    return ConfigResponse(
        gbp_to_usd_rate=float(configs.get("gbp_to_usd_rate", 1.28)),
        eur_to_usd_rate=float(configs.get("eur_to_usd_rate", 1.10)),
    )


@router.put("/config", response_model=ConfigResponse)
def update_config(
    updates: ConfigUpdate, db: Session = Depends(get_db), _user=Depends(require_admin)
):
    """Update admin configuration (admin only)."""
    for key, value in updates.model_dump(exclude_none=True).items():
        config = db.get(AdminConfig, key)
        if config:
            config.value = value
        else:
            db.add(AdminConfig(key=key, value=value))
    db.commit()
    return get_config(db)


@router.get("/system-info", response_model=SystemInfoResponse)
def get_system_info(db: Session = Depends(get_db)):
    """Get comprehensive system information for admin dashboard.

    Returns version info, health checks, scoring configuration,
    and tiered entities (authors, publishers, binders).
    """
    import time

    start = time.time()

    # Get cold start status
    is_cold_start = get_cold_start_status()

    # Get version info
    version_info = get_version_info()

    # Run health checks
    db_health = check_database(db)
    s3_health = check_s3()
    cognito_health = check_cognito()

    # Determine overall health
    statuses = [db_health["status"], s3_health["status"], cognito_health["status"]]
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
            ),
        ),
        models={
            name: ModelInfo(model_id=model_id, usage=MODEL_USAGE.get(name, ""))
            for name, model_id in MODEL_IDS.items()
        },
        scoring_config=get_scoring_config(),
        entity_tiers=EntityTiers(
            authors=[EntityTier(name=a.name, tier=a.tier) for a in authors],
            publishers=[EntityTier(name=p.name, tier=p.tier) for p in publishers],
            binders=[EntityTier(name=b.name, tier=b.tier) for b in binders],
        ),
    )
