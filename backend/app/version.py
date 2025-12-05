"""Application version management."""

import os
from functools import lru_cache
from pathlib import Path


@lru_cache
def get_version() -> str:
    """Get application version from VERSION file.

    Looks for VERSION file in:
    1. Parent of backend directory (repo root)
    2. Current working directory
    3. Falls back to "0.0.0-dev"
    """
    # Try repo root (parent of backend/)
    version_file = Path(__file__).parent.parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()

    # Try current working directory
    cwd_version = Path.cwd() / "VERSION"
    if cwd_version.exists():
        return cwd_version.read_text().strip()

    # Fallback for local development
    return "0.0.0-dev"


def get_git_sha() -> str:
    """Get git SHA from environment (set during CI/CD)."""
    return os.getenv("GIT_SHA", "unknown")


def get_deployed_at() -> str:
    """Get deployment timestamp from environment (set during CI/CD)."""
    return os.getenv("DEPLOYED_AT", "unknown")


def get_version_info() -> dict:
    """Get complete version information."""
    from app.config import get_settings

    settings = get_settings()
    return {
        "version": get_version(),
        "environment": settings.environment,
        "git_sha": get_git_sha(),
        "deployed_at": get_deployed_at(),
    }
