"""Entity profile API endpoints."""

import io
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Path, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image, ImageOps
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.auth import require_admin, require_editor, require_viewer
from app.config import get_settings
from app.db import get_db
from app.models import ENTITY_MODEL_MAP
from app.models.entity_profile import EntityProfile
from app.models.profile_generation_job import JobStatus, ProfileGenerationJob
from app.schemas.entity_profile import EntityProfileResponse, EntityType
from app.services.aws_clients import get_s3_client
from app.services.entity_profile import (
    _get_all_collection_entities,
    _get_entity_books,
    get_entity_profile,
)
from app.services.sqs import send_profile_generation_jobs
from app.utils.cdn import get_cloudfront_cdn_url

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/profiles/generate-all",
    summary="Generate all entity profiles (async)",
    description="Admin-only: enqueues async profile generation for all entities.",
)
def generate_all_profiles(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Enqueue async profile generation for all entities.

    Returns a job ID for progress tracking. If an in-progress job exists,
    returns that job instead of creating a new one.
    """
    if not current_user.db_user:
        raise HTTPException(status_code=403, detail="API key auth requires linked database user")

    # Check for existing in-progress job
    existing = (
        db.query(ProfileGenerationJob)
        .filter(ProfileGenerationJob.status.in_(JobStatus.ACTIVE))
        .first()
    )
    if existing:
        return {
            "job_id": existing.id,
            "total_entities": existing.total_entities,
            "status": existing.status,
        }

    # Collect only entities that have at least one qualifying (owned) book.
    # This prevents generating profiles for entities tied only to EVALUATING/REMOVED books (#1866).
    collection_entities = _get_all_collection_entities(db)
    entities = [(e["entity_type"], e["entity_id"]) for e in collection_entities]

    if not entities:
        return {"job_id": None, "total_entities": 0, "status": "empty"}

    # Create job record
    job = ProfileGenerationJob(
        owner_id=current_user.db_user.id,
        status=JobStatus.PENDING,
        total_entities=len(entities),
    )
    db.add(job)
    db.commit()

    # Enqueue SQS messages
    messages = [
        {
            "job_id": job.id,
            "entity_type": entity_type,
            "entity_id": entity_id,
        }
        for entity_type, entity_id in entities
    ]
    try:
        send_profile_generation_jobs(messages)
    except Exception as exc:
        logger.exception("Failed to enqueue profile generation messages for job %s", job.id)
        job.status = JobStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=500, detail="Failed to enqueue generation messages"
        ) from exc

    job.status = JobStatus.IN_PROGRESS
    db.commit()

    return {
        "job_id": job.id,
        "total_entities": len(entities),
        "status": JobStatus.IN_PROGRESS,
    }


@router.post(
    "/profiles/generate-all/{job_id}/cancel",
    summary="Cancel a profile generation job",
    description="Admin-only: cancel an in-progress or pending profile generation job.",
)
def cancel_generation_job(
    job_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Cancel a stale or stuck profile generation job.

    Marks the job as 'cancelled' with a completed_at timestamp so that
    generate-all can create a new job.
    """
    if not current_user.db_user:
        raise HTTPException(status_code=403, detail="API key auth requires linked database user")

    # Atomic UPDATE avoids TOCTOU race between status check and write
    now = datetime.now(UTC)
    result = db.execute(
        update(ProfileGenerationJob)
        .where(
            ProfileGenerationJob.id == job_id,
            ProfileGenerationJob.status.in_(JobStatus.ACTIVE),
        )
        .values(status=JobStatus.CANCELLED, completed_at=now)
    )
    db.commit()

    if result.rowcount == 0:
        # Distinguish 404 (not found) from 409 (exists but terminal)
        job = db.query(ProfileGenerationJob).filter(ProfileGenerationJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        raise HTTPException(
            status_code=409,
            detail=f"Job {job_id} is already {job.status} and cannot be cancelled",
        )

    return {
        "job_id": job_id,
        "status": JobStatus.CANCELLED,
        "completed_at": now.isoformat(),
    }


@router.get(
    "/profiles/generate-all/status/{job_id}",
    summary="Get batch generation job status",
)
def get_generation_status(
    job_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Get progress of a batch profile generation job."""
    job = db.query(ProfileGenerationJob).filter(ProfileGenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return {
        "job_id": job.id,
        "status": job.status,
        "total_entities": job.total_entities,
        "succeeded": job.succeeded,
        "failed": job.failed,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.get(
    "/{entity_type}/{entity_id}/profile",
    response_model=EntityProfileResponse,
    summary="Get entity profile",
    description="Returns full profile for an entity including bio, connections, books, and stats.",
)
def get_profile(
    entity_type: EntityType = Path(..., description="Entity type: author, publisher, or binder"),
    entity_id: int = Path(..., ge=1, description="Entity database ID"),
    db: Session = Depends(get_db),
    current_user=Depends(require_viewer),
) -> EntityProfileResponse:
    """Get entity profile with AI-generated content if available."""
    if not current_user.db_user:
        raise HTTPException(status_code=403, detail="API key auth requires linked database user")
    result = get_entity_profile(db, entity_type.value, entity_id)
    if not result:
        raise HTTPException(
            status_code=404, detail=f"Entity {entity_type.value}:{entity_id} not found"
        )
    return result


@router.post(
    "/{entity_type}/{entity_id}/profile/regenerate",
    status_code=202,
    summary="Regenerate entity profile (async)",
    description="Deletes cached profile and enqueues async regeneration via SQS.",
)
def regenerate_profile(
    entity_type: EntityType = Path(...),
    entity_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_editor),
):
    """Enqueue async profile regeneration via SQS.

    Deletes existing cached profile so the UI shows a loading state,
    then sends a message to the profile generation queue. The profile
    worker Lambda picks up the message and generates the new profile.

    Returns 202 Accepted immediately -- the caller should poll
    GET /{entity_type}/{entity_id}/profile until the profile reappears.
    """
    if not current_user.db_user:
        raise HTTPException(status_code=403, detail="API key auth requires linked database user")

    # Validate entity exists
    model = _PORTRAIT_MODEL_MAP.get(entity_type.value)
    if not model:
        raise HTTPException(
            status_code=404, detail=f"Entity {entity_type.value}:{entity_id} not found"
        )
    entity = db.query(model).filter(model.id == entity_id).first()
    if not entity:
        raise HTTPException(
            status_code=404, detail=f"Entity {entity_type.value}:{entity_id} not found"
        )

    # Guard: only regenerate profiles for entities with qualifying books
    qualifying_books = _get_entity_books(db, entity_type.value, entity_id)
    if not qualifying_books:
        raise HTTPException(
            status_code=409,
            detail=f"Entity {entity_type.value}:{entity_id} has no qualifying books (IN_TRANSIT/ON_HAND)",
        )

    # Enqueue async regeneration via SQS first — if this fails, the old
    # profile is preserved (no data-loss window).
    message = {
        "job_id": None,
        "entity_type": entity_type.value,
        "entity_id": entity_id,
    }
    try:
        send_profile_generation_jobs([message])
    except Exception as exc:
        logger.exception(
            "Failed to enqueue profile regeneration for %s:%s",
            entity_type.value,
            entity_id,
        )
        raise HTTPException(
            status_code=500, detail="Failed to enqueue profile regeneration"
        ) from exc

    # Delete existing cached profile so the UI shows loading state.
    # Done after enqueue so a failure above doesn't leave the profile deleted.
    db.query(EntityProfile).filter(
        EntityProfile.entity_type == entity_type.value,
        EntityProfile.entity_id == entity_id,
    ).delete()
    db.commit()

    return JSONResponse(
        status_code=202,
        content={"status": "queued", "message": "Profile regeneration queued"},
    )


# Use shared entity-type-to-model mapping for portrait upload.
_PORTRAIT_MODEL_MAP = ENTITY_MODEL_MAP

# Portrait image settings.
PORTRAIT_SIZE = (400, 400)
PORTRAIT_QUALITY = 85
PORTRAIT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


@router.put(
    "/{entity_type}/{entity_id}/portrait",
    summary="Upload entity portrait image",
    description="Admin-only: upload or replace the portrait image for an entity.",
)
async def upload_entity_portrait(
    entity_type: str = Path(..., description="Entity type: author, publisher, or binder"),
    entity_id: int = Path(..., ge=1, description="Entity database ID"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """Upload a portrait image for an entity.

    Resizes to 400x400 JPEG, uploads to S3, and updates the entity's image_url.
    """
    # Validate entity type
    model = _PORTRAIT_MODEL_MAP.get(entity_type)
    if not model:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity type: {entity_type}. Must be author, publisher, or binder.",
        )

    # Verify entity exists
    entity = db.query(model).filter(model.id == entity_id).first()
    if not entity:
        raise HTTPException(
            status_code=404,
            detail=f"Entity {entity_type}:{entity_id} not found",
        )

    # Read and validate image
    content = await file.read()
    if len(content) > PORTRAIT_MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({len(content)} bytes). Maximum is {PORTRAIT_MAX_BYTES} bytes.",
        )

    try:
        img = Image.open(io.BytesIO(content))
        img = ImageOps.exif_transpose(img)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid image file. Supported formats: JPEG, PNG, WEBP.",
        ) from exc

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img = img.resize(PORTRAIT_SIZE, Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, "JPEG", quality=PORTRAIT_QUALITY)
    buffer.seek(0)

    # Upload to S3
    s3_key = f"entities/{entity_type}/{entity_id}/portrait.jpg"
    settings = get_settings()
    s3 = get_s3_client()
    s3.upload_fileobj(
        buffer,
        settings.images_bucket,
        s3_key,
        ExtraArgs={"ContentType": "image/jpeg"},
    )

    # Update entity's image_url with CloudFront URL
    cdn_url = get_cloudfront_cdn_url()
    entity.image_url = f"{cdn_url}/{s3_key}"
    db.commit()

    return {"image_url": entity.image_url, "s3_key": s3_key}
