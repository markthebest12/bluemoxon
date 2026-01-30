"""Entity profile API endpoints."""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.auth import require_admin, require_editor, require_viewer
from app.db import get_db
from app.models.author import Author
from app.models.binder import Binder
from app.models.publisher import Publisher
from app.schemas.entity_profile import EntityProfileResponse, EntityType
from app.services.entity_profile import generate_and_cache_profile, get_entity_profile

logger = logging.getLogger(__name__)

BATCH_SIZE = 10

router = APIRouter()


@router.post(
    "/profiles/generate-all",
    summary="Generate all entity profiles",
    description="Admin-only: generates AI profiles for all entities in batches.",
)
def generate_all_profiles(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Batch generate profiles for all entities.

    Note: This endpoint may exceed API Gateway's 29s timeout for large collections.
    For large batches, invoke the Lambda directly or use the CLI.
    Connection narratives are capped at MAX_NARRATIVES_PER_ENTITY per entity to
    limit API call volume.
    """
    results = {"total": 0, "succeeded": 0, "failed": 0}

    entities = []
    for entity_type, model in [("author", Author), ("publisher", Publisher), ("binder", Binder)]:
        for entity in db.query(model).all():
            entities.append((entity_type, entity.id))

    results["total"] = len(entities)

    for i in range(0, len(entities), BATCH_SIZE):
        batch = entities[i : i + BATCH_SIZE]
        for entity_type, entity_id in batch:
            try:
                generate_and_cache_profile(
                    db, entity_type, entity_id, current_user.db_user.id, max_narratives=3
                )
                results["succeeded"] += 1
            except Exception:
                logger.exception("Failed to generate profile for %s:%s", entity_type, entity_id)
                results["failed"] += 1

        if i + BATCH_SIZE < len(entities):
            time.sleep(1)

    return results


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
    try:
        generate_and_cache_profile(db, entity_type.value, entity_id, current_user.db_user.id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404, detail=f"Entity {entity_type.value}:{entity_id} not found"
        ) from exc
    return {"status": "regenerated"}
