"""Public configuration endpoints.

These endpoints return non-sensitive configuration data (e.g. model labels)
and do NOT require authentication.  Admin-only config lives in admin.py.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.bedrock import MODEL_DISPLAY_NAMES

router = APIRouter()


class ModelLabelsResponse(BaseModel):
    """Map of model key to human-readable display name."""

    labels: dict[str, str]


@router.get("/model-labels", response_model=ModelLabelsResponse)
def get_model_labels():
    """Return display labels for all active AI models.

    Public endpoint — no authentication required.
    Used by the frontend to render friendly model names in analysis views.
    """
    return ModelLabelsResponse(labels=MODEL_DISPLAY_NAMES)
