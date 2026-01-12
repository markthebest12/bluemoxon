"""Tests for books GET endpoint authentication."""

import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models import Author, Book
from app.models.base import Base
from tests.conftest import TestingSessionLocal, engine


class TestBooksGetAuth:
    """Tests for books GET endpoint authentication requirements."""

    @pytest.fixture
    def unauthenticated_client(self, db):
        """Client without auth overrides."""

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    @pytest.fixture
    def db(self):
        """Create a fresh database for each test."""
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
            Base.metadata.drop_all(bind=engine)

    @pytest.fixture
    def sample_book(self, db):
        """Create a sample book for testing."""
        author = Author(name="Test Author")
        db.add(author)
        db.flush()
        book = Book(
            title="Test Book",
            author_id=author.id,
            inventory_type="PRIMARY",
            status="ON_HAND",
        )
        db.add(book)
        db.commit()
        db.refresh(book)
        return book

    def test_books_list_requires_auth(self, unauthenticated_client):
        """Test that GET /books returns 401 without authentication."""
        response = unauthenticated_client.get("/api/v1/books")
        assert response.status_code == 401

    def test_books_get_requires_auth(self, unauthenticated_client, sample_book):
        """Test that GET /books/{id} returns 401 without authentication."""
        response = unauthenticated_client.get(f"/api/v1/books/{sample_book.id}")
        assert response.status_code == 401

    def test_books_analysis_requires_auth(self, unauthenticated_client, sample_book):
        """Test that GET /books/{id}/analysis returns 401 without authentication."""
        response = unauthenticated_client.get(f"/api/v1/books/{sample_book.id}/analysis")
        assert response.status_code == 401

    def test_books_analysis_raw_requires_auth(self, unauthenticated_client, sample_book):
        """Test that GET /books/{id}/analysis/raw returns 401 without authentication."""
        response = unauthenticated_client.get(f"/api/v1/books/{sample_book.id}/analysis/raw")
        assert response.status_code == 401

    def test_books_scores_requires_auth(self, unauthenticated_client, sample_book):
        """Test that GET /books/{id}/scores/breakdown returns 401 without authentication."""
        response = unauthenticated_client.get(f"/api/v1/books/{sample_book.id}/scores/breakdown")
        assert response.status_code == 401

    def test_books_list_works_with_auth(self, client):
        """Test that GET /books works with authentication."""
        response = client.get("/api/v1/books")
        assert response.status_code == 200

    def test_books_get_works_with_auth(self, client, sample_book):
        """Test that GET /books/{id} works with authentication."""
        response = client.get(f"/api/v1/books/{sample_book.id}")
        assert response.status_code == 200
