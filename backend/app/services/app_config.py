"""Application configuration service with in-process caching.

Cache is module-level and single-threaded (safe for Lambda, not for
multi-threaded servers). See _cache docstring below.
"""

import logging
import time

from sqlalchemy.orm import Session

from app.models.app_config import AppConfig

logger = logging.getLogger(__name__)

# Module-level cache: maps key → (value_or_None, timestamp).
# Single-threaded; safe for Lambda. For multi-threaded use, wrap with a Lock.
_MISSING = "__MISSING__"  # sentinel cached when DB row does not exist
_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL = 300  # 5 minutes


def get_config(db: Session, key: str, default: str | None = None) -> str | None:
    """Get a config value, with in-process caching.

    Caches both found values and cache-misses (row not in DB) to avoid
    stale phantom values when a row is deleted.

    Args:
        db: Database session.
        key: Configuration key to look up.
        default: Default value if key not found.

    Returns:
        The configuration value, or default if not found.
    """
    now = time.time()
    if key in _cache and now - _cache[key][1] < CACHE_TTL:
        cached = _cache[key][0]
        return default if cached == _MISSING else cached

    row = db.query(AppConfig).filter(AppConfig.key == key).first()
    if row:
        _cache[key] = (row.value, now)
        return row.value
    else:
        _cache[key] = (_MISSING, now)
        return default


def set_config(
    db: Session,
    key: str,
    value: str,
    description: str | None = None,
    updated_by: str | None = None,
) -> None:
    """Set a config value (upsert).

    Flushes to the session but does NOT commit — the caller owns
    transaction boundaries.

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
    db.flush()
    _cache.pop(key, None)  # Invalidate cache on write


def clear_cache() -> None:
    """Clear the in-process config cache. Useful for testing."""
    _cache.clear()
