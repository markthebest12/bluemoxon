"""Application version management."""

import os
from functools import lru_cache
from pathlib import Path


@lru_cache
def get_version() -> str:
    """Get application version from VERSION file.

    Looks for VERSION file in:
    1. Lambda package root (/var/task in Lambda, backend/ locally)
    2. Repo root (for local dev when running from backend/)
    3. Current working directory
    4. Falls back to "0.0.0-dev"
    """
    # Try Lambda/package root: app/version.py -> app -> /var/task (or backend/)
    lambda_version = Path(__file__).parent.parent / "VERSION"
    if lambda_version.exists():
        return lambda_version.read_text().strip()

    # Try repo root (parent of backend/ for local dev)
    repo_version = Path(__file__).parent.parent.parent / "VERSION"
    if repo_version.exists():
        return repo_version.read_text().strip()

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
