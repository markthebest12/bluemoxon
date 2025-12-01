"""Test fixtures and configuration."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import CurrentUser, require_editor
from app.db import get_db
from app.main import app
from app.models.base import Base


# Mock editor user for tests
def get_mock_editor():
    """Return a mock editor user for tests."""
    return CurrentUser(
        cognito_sub="test-user-123",
        email="test@example.com",
        role="editor",
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
    """Create a test client with database override and mock auth."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_editor] = get_mock_editor
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
