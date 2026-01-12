"""Tests for books GET endpoint authentication.

Uses shared fixtures from conftest.py:
- db: Fresh database for each test
- unauthenticated_client: Client without auth (expects 401)
- client: Client with full auth (expects 200)
"""

import pytest

from app.models import Author, Book


class TestBooksGetAuth:
    """Tests for books GET endpoint authentication requirements."""

    @pytest.fixture
    def sample_book(self, db):
        """Create a sample book for testing.

        Uses the shared db fixture from conftest.py to ensure the book
        is visible to both unauthenticated_client and client fixtures.
        """
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

    # Unauthenticated access tests (401)
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

    # Authenticated access tests (200)
    def test_books_list_works_with_auth(self, client):
        """Test that GET /books works with authentication."""
        response = client.get("/api/v1/books")
        assert response.status_code == 200

    def test_books_get_works_with_auth(self, client, sample_book):
        """Test that GET /books/{id} works with authentication."""
        response = client.get(f"/api/v1/books/{sample_book.id}")
        assert response.status_code == 200

    def test_books_scores_works_with_auth(self, client, sample_book):
        """Test that GET /books/{id}/scores/breakdown works with authentication."""
        response = client.get(f"/api/v1/books/{sample_book.id}/scores/breakdown")
        assert response.status_code == 200
