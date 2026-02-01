"""Profile generation worker -- processes SQS messages for async batch generation."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import update

from app.db import SessionLocal
from app.models.entity_profile import EntityProfile
from app.models.profile_generation_job import JobStatus, ProfileGenerationJob
from app.services.entity_profile import generate_and_cache_profile
from app.services.social_circles_cache import get_or_build_graph

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _check_staleness(db: Session, entity_type: str, entity_id: int, owner_id: int) -> bool:
    """Check if entity needs profile generation.

    Returns True if entity has no profile or profile is stale.
    """
    profile = (
        db.query(EntityProfile)
        .filter(
            EntityProfile.entity_type == entity_type,
            EntityProfile.entity_id == entity_id,
            EntityProfile.owner_id == owner_id,
        )
        .first()
    )
    if not profile or not profile.generated_at:
        return True  # No profile = needs generation

    from app.services.entity_profile import _check_staleness as check_stale

    return check_stale(db, profile, entity_type, entity_id)


def _update_job_progress(db: Session, job_id: str, success: bool, error: str | None = None) -> None:
    """Atomically update job progress and check for completion."""
    increment = {
        ProfileGenerationJob.updated_at: datetime.now(UTC),
    }
    if success:
        increment[ProfileGenerationJob.succeeded] = ProfileGenerationJob.succeeded + 1
    else:
        increment[ProfileGenerationJob.failed] = ProfileGenerationJob.failed + 1
    db.execute(
        update(ProfileGenerationJob).where(ProfileGenerationJob.id == job_id).values(increment)
    )
    if error:
        job = db.query(ProfileGenerationJob).filter(ProfileGenerationJob.id == job_id).first()
        if job:
            existing = job.error_log or ""
            job.error_log = (existing + "\n" + error).strip()
    db.commit()

    # Check completion (skip if job was cancelled by admin or already completed)
    job = db.query(ProfileGenerationJob).filter(ProfileGenerationJob.id == job_id).first()
    if (
        job
        and job.status not in JobStatus.TERMINAL
        and (job.succeeded + job.failed) >= job.total_entities
    ):
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        db.commit()


def handle_profile_generation_message(message: dict, db: Session) -> None:
    """Process a single profile generation message.

    Args:
        message: Dict with keys: job_id, entity_type, entity_id, owner_id
        db: Database session
    """
    job_id = message["job_id"]
    entity_type = message["entity_type"]
    entity_id = message["entity_id"]
    owner_id = message["owner_id"]

    try:
        # Idempotency: skip if entity already has a non-stale profile
        if not _check_staleness(db, entity_type, entity_id, owner_id):
            logger.info("Skipping %s:%s (profile is current)", entity_type, entity_id)
            _update_job_progress(db, job_id, success=True)
            return

        # Get cached graph (first worker builds, rest get cache hits)
        graph = get_or_build_graph(db)

        # Generate profile
        generate_and_cache_profile(
            db,
            entity_type,
            entity_id,
            owner_id,
            max_narratives=3,
            graph=graph,
        )

        logger.info("Generated profile for %s:%s", entity_type, entity_id)
        _update_job_progress(db, job_id, success=True)

    except Exception as exc:
        logger.exception("Failed to generate profile for %s:%s", entity_type, entity_id)
        _update_job_progress(db, job_id, success=False, error=f"{entity_type}:{entity_id}: {exc}")


def handler(event: dict, context) -> dict:
    """Lambda handler for SQS profile generation messages.

    Also supports version check via {"version": true} payload.

    Args:
        event: SQS event containing batch of messages, or version check payload
        context: Lambda context

    Returns:
        Dict with batch item failures for partial batch response,
        or version info if version check requested
    """
    from app.config import get_settings

    # Handle version check (for smoke tests)
    if event.get("version"):
        settings = get_settings()
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "version": getattr(settings, "app_version", "unknown"),
                    "worker": "profile-generation",
                }
            ),
        }

    batch_item_failures = []

    for record in event.get("Records", []):
        message_id = record.get("messageId", "unknown")

        try:
            body = json.loads(record["body"])
            logger.info(
                "Processing profile generation for %s:%s",
                body.get("entity_type"),
                body.get("entity_id"),
            )

            db = SessionLocal()
            try:
                handle_profile_generation_message(body, db)
            finally:
                db.close()

            logger.info("Successfully processed message %s", message_id)

        except Exception:
            logger.exception("Failed to process message %s", message_id)
            batch_item_failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": batch_item_failures}
