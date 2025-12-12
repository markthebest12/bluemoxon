"""Admin configuration API endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.db.session import get_db
from app.models.admin_config import AdminConfig

router = APIRouter()


class ConfigResponse(BaseModel):
    """Admin config response."""

    gbp_to_usd_rate: float
    eur_to_usd_rate: float


class ConfigUpdate(BaseModel):
    """Admin config update request."""

    gbp_to_usd_rate: float | None = None
    eur_to_usd_rate: float | None = None


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
