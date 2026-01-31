"""Entity profile API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.auth import require_admin, require_editor, require_viewer
from app.db import get_db
from app.models.author import Author
from app.models.binder import Binder
from app.models.profile_generation_job import ProfileGenerationJob
from app.models.publisher import Publisher
from app.schemas.entity_profile import EntityProfileResponse, EntityType
from app.services.entity_profile import generate_and_cache_profile, get_entity_profile
from app.services.social_circles_cache import get_or_build_graph
from app.services.sqs import send_profile_generation_jobs

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
        .filter(ProfileGenerationJob.status.in_(["pending", "in_progress"]))
        .first()
    )
    if existing:
        return {
            "job_id": existing.id,
            "total_entities": existing.total_entities,
            "status": existing.status,
        }

    # Collect all entities
    entities = []
    for entity_type, model in [("author", Author), ("publisher", Publisher), ("binder", Binder)]:
        for entity in db.query(model).all():
            entities.append((entity_type, entity.id))

    # Create job record
    job = ProfileGenerationJob(
        owner_id=current_user.db_user.id,
        status="pending",
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
            "owner_id": current_user.db_user.id,
        }
        for entity_type, entity_id in entities
    ]
    send_profile_generation_jobs(messages)

    return {
        "job_id": job.id,
        "total_entities": len(entities),
        "status": "pending",
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
    result = get_entity_profile(db, entity_type.value, entity_id, current_user.db_user.id)
    if not result:
        raise HTTPException(
            status_code=404, detail=f"Entity {entity_type.value}:{entity_id} not found"
        )
    return result


@router.post(
    "/{entity_type}/{entity_id}/profile/regenerate",
    summary="Regenerate entity profile",
    description="Triggers regeneration of AI-generated profile content.",
)
def regenerate_profile(
    entity_type: EntityType = Path(...),
    entity_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_editor),
):
    """Regenerate AI profile content. Requires editor role due to API cost."""
    if not current_user.db_user:
        raise HTTPException(status_code=403, detail="API key auth requires linked database user")
    try:
        graph = get_or_build_graph(db)
        generate_and_cache_profile(
            db, entity_type.value, entity_id, current_user.db_user.id, graph=graph
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404, detail=f"Entity {entity_type.value}:{entity_id} not found"
        ) from exc
    return {"status": "regenerated"}
