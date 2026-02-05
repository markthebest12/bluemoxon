"""Profile generation worker -- processes SQS messages for async batch generation."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import update

from app.db import SessionLocal
from app.models.profile_generation_job import JobStatus, ProfileGenerationJob
from app.services.entity_profile import (
    _get_all_collection_entities,
    generate_and_cache_profile,
    is_profile_stale,
)
from app.services.social_circles_cache import get_or_build_graph

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


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


def handle_profile_generation_message(
    message: dict, db: Session, all_entities: list[dict] | None = None
) -> None:
    """Process a single profile generation message.

    Args:
        message: Dict with keys: job_id (nullable), entity_type, entity_id.
                 job_id is None for ad-hoc single-entity regeneration requests.
        db: Database session
        all_entities: Pre-computed collection entities (avoids N repeated queries in batch)
    """
    job_id = message.get("job_id")
    entity_type = message["entity_type"]
    entity_id = message["entity_id"]

    try:
        # Idempotency: skip if entity already has a non-stale profile
        if not is_profile_stale(db, entity_type, entity_id):
            logger.info("Skipping %s:%s (profile is current)", entity_type, entity_id)
            if job_id:
                _update_job_progress(db, job_id, success=True)
            return

        # Get cached graph (first worker builds, rest get cache hits)
        graph = get_or_build_graph(db)

        # Generate profile
        generate_and_cache_profile(
            db,
            entity_type,
            entity_id,
            max_narratives=3,
            graph=graph,
            all_entities=all_entities,
        )

        logger.info("Generated profile for %s:%s", entity_type, entity_id)
        if job_id:
            _update_job_progress(db, job_id, success=True)

    except Exception as exc:
        logger.exception("Failed to generate profile for %s:%s", entity_type, entity_id)
        if job_id:
            _update_job_progress(
                db, job_id, success=False, error=f"{entity_type}:{entity_id}: {exc}"
            )


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

    # Pre-compute collection entities once per batch to avoid N repeated queries (#1803)
    all_entities: list[dict] | None = None
    if len(event.get("Records", [])) > 1:
        try:
            db = SessionLocal()
            try:
                all_entities = _get_all_collection_entities(db)
            finally:
                db.close()
        except Exception:
            logger.warning("Failed to pre-compute collection entities, will compute per-message")

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
                handle_profile_generation_message(body, db, all_entities=all_entities)
            finally:
                db.close()

            logger.info("Successfully processed message %s", message_id)

        except Exception:
            logger.exception("Failed to process message %s", message_id)
            batch_item_failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": batch_item_failures}
