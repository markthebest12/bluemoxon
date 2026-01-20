"""Pytest fixtures for scripts tests."""

from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def scripts_dir(project_root: Path) -> Path:
    """Return the scripts directory."""
    return project_root / "scripts"


@pytest.fixture
def backend_config_path(project_root: Path) -> Path:
    """Return the path to backend/app/config.py."""
    return project_root / "backend" / "app" / "config.py"
