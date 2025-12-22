"""Application version management."""

import json
from functools import lru_cache
from pathlib import Path


def _find_file(filename: str) -> Path | None:
    """Find a file in standard locations.

    Looks in:
    1. Lambda package root (/var/task in Lambda, backend/ locally)
    2. Repo root (for local dev when running from backend/)
    3. Current working directory
    """
    # Try Lambda/package root: app/version.py -> app -> /var/task (or backend/)
    lambda_path = Path(__file__).parent.parent / filename
    if lambda_path.exists():
        return lambda_path

    # Try repo root (parent of backend/ for local dev)
    repo_path = Path(__file__).parent.parent.parent / filename
    if repo_path.exists():
        return repo_path

    # Try current working directory
    cwd_path = Path.cwd() / filename
    if cwd_path.exists():
        return cwd_path

    return None


@lru_cache
def get_version() -> str:
    """Get application version from VERSION file.

    Falls back to "0.0.0-dev" for local development.
    """
    version_file = _find_file("VERSION")
    if version_file:
        return version_file.read_text().strip()
    return "0.0.0-dev"


@lru_cache
def _get_version_info_json() -> dict:
    """Load version_info.json if available.

    This file is created during CI/CD and contains git_sha and deployed_at.
    Returns empty dict if file not found (local development).
    """
    info_file = _find_file("version_info.json")
    if info_file:
        try:
            return json.loads(info_file.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def get_git_sha() -> str:
    """Get git SHA from version_info.json (set during CI/CD)."""
    return _get_version_info_json().get("git_sha", "unknown")


def get_deployed_at() -> str:
    """Get deployment timestamp from version_info.json (set during CI/CD)."""
    return _get_version_info_json().get("deployed_at", "unknown")


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
