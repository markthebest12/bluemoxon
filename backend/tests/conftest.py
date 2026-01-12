"""Test fixtures and configuration."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import (
    CurrentUser,
    get_current_user,
    require_admin,
    require_editor,
    require_viewer,
)
from app.db import get_db
from app.main import app
from app.models.base import Base


# Mock viewer user for tests (lowest privilege level)
def get_mock_viewer():
    """Return a mock viewer user for tests."""
    return CurrentUser(
        cognito_sub="test-viewer-123",
        email="viewer@example.com",
        role="viewer",
        db_user=None,
    )


# Mock editor user for tests
def get_mock_editor():
    """Return a mock editor user for tests."""
    return CurrentUser(
        cognito_sub="test-user-123",
        email="test@example.com",
        role="editor",
        db_user=None,
    )


# Mock admin user for tests
def get_mock_admin():
    """Return a mock admin user for tests."""
    return CurrentUser(
        cognito_sub="test-admin-123",
        email="admin@example.com",
        role="admin",
        db_user=None,
    )


# Use DATABASE_URL from environment (CI uses PostgreSQL) or SQLite for local
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # PostgreSQL in CI
    engine = create_engine(DATABASE_URL)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    # SQLite in-memory for fast local tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client with database override and mock auth (admin level)."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_viewer] = get_mock_editor
    app.dependency_overrides[require_editor] = get_mock_editor
    app.dependency_overrides[require_admin] = get_mock_admin
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def unauthenticated_client(db):
    """Create a test client without auth overrides (401 expected)."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def viewer_client(db):
    """Create a test client with viewer-level auth (403 expected on admin endpoints).

    Overrides get_current_user to return a viewer user, allowing the actual
    role check in require_admin to run and return 403 for non-admin users.
    """

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    # Override get_current_user to return viewer (bypasses 401 auth check)
    # This allows require_admin to run its is_admin check and return 403
    app.dependency_overrides[get_current_user] = get_mock_viewer
    app.dependency_overrides[require_viewer] = get_mock_viewer
    app.dependency_overrides[require_editor] = get_mock_viewer
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
