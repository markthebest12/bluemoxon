"""Application configuration service with in-process caching."""

import logging
import time

from sqlalchemy.orm import Session

from app.models.app_config import AppConfig

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL = 300  # 5 minutes


def get_config(db: Session, key: str, default: str | None = None) -> str | None:
    """Get a config value, with in-process caching.

    Args:
        db: Database session.
        key: Configuration key to look up.
        default: Default value if key not found.

    Returns:
        The configuration value, or default if not found.
    """
    now = time.time()
    if key in _cache and now - _cache[key][1] < CACHE_TTL:
        return _cache[key][0]

    row = db.query(AppConfig).filter(AppConfig.key == key).first()
    value = row.value if row else default
    if value is not None:
        _cache[key] = (value, now)
    return value


def set_config(
    db: Session,
    key: str,
    value: str,
    description: str | None = None,
    updated_by: str | None = None,
) -> None:
    """Set a config value (upsert).

    Args:
        db: Database session.
        key: Configuration key to set.
        value: New value.
        description: Optional description of this config key.
        updated_by: Optional identifier of who made the change.
    """
    row = db.query(AppConfig).filter(AppConfig.key == key).first()
    if row:
        row.value = value
        if description is not None:
            row.description = description
        if updated_by is not None:
            row.updated_by = updated_by
    else:
        row = AppConfig(
            key=key,
            value=value,
            description=description,
            updated_by=updated_by,
        )
        db.add(row)
    db.commit()
    _cache.pop(key, None)  # Invalidate cache on write


def clear_cache() -> None:
    """Clear the in-process config cache. Useful for testing."""
    _cache.clear()
