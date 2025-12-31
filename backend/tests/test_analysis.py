"""Analysis API tests."""

from datetime import datetime


class TestGetAnalysis:
    """Tests for GET /api/v1/books/{id}/analysis."""

    def test_get_analysis_not_found(self, client):
        """Test 404 when book has no analysis."""
        # Create a book
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Try to get analysis
        response = client.get(f"/api/v1/books/{book_id}/analysis")
        assert response.status_code == 404
        assert "No analysis available" in response.json()["detail"]

    def test_get_analysis_book_not_found(self, client):
        """Test 404 when book doesn't exist."""
        response = client.get("/api/v1/books/999/analysis")
        assert response.status_code == 404

    def test_get_analysis_includes_generated_at(self, client):
        """Test that analysis response includes generated_at timestamp."""
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        client.put(
            f"/api/v1/books/{book_id}/analysis",
            content="# Test Analysis\n\n## Executive Summary\nTest content.",
            headers={"Content-Type": "text/plain"},
        )

        response = client.get(f"/api/v1/books/{book_id}/analysis")
        assert response.status_code == 200

        data = response.json()
        assert "generated_at" in data
        assert data["generated_at"] is not None

        parsed = datetime.fromisoformat(data["generated_at"])
        assert parsed.tzinfo is not None

    def test_get_analysis_includes_model_id(self, client):
        """Test that analysis response includes model_id field."""
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Upload analysis via PUT (simulates manual upload - no model_id)
        client.put(
            f"/api/v1/books/{book_id}/analysis",
            content="# Test Analysis\n\n## Executive Summary\nTest content.",
            headers={"Content-Type": "text/plain"},
        )

        response = client.get(f"/api/v1/books/{book_id}/analysis")
        assert response.status_code == 200

        data = response.json()
        # model_id should be present in response (null for manual uploads)
        assert "model_id" in data

    def test_legacy_analysis_has_null_model_id(self, client):
        """Test that existing/legacy analyses return null model_id."""
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Upload analysis without model_id (simulates legacy data)
        client.put(
            f"/api/v1/books/{book_id}/analysis",
            content="# Legacy Analysis\n\n## Executive Summary\nOld content.",
            headers={"Content-Type": "text/plain"},
        )

        response = client.get(f"/api/v1/books/{book_id}/analysis")
        assert response.status_code == 200

        data = response.json()
        assert "model_id" in data
        assert data["model_id"] is None  # Legacy should be null


class TestGetAnalysisRaw:
    """Tests for GET /api/v1/books/{id}/analysis/raw."""

    def test_get_analysis_raw_not_found(self, client):
        """Test 404 when book has no analysis."""
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        response = client.get(f"/api/v1/books/{book_id}/analysis/raw")
        assert response.status_code == 404

    def test_get_analysis_raw_book_not_found(self, client):
        """Test 404 when book doesn't exist."""
        response = client.get("/api/v1/books/999/analysis/raw")
        assert response.status_code == 404


class TestUpdateAnalysis:
    """Tests for PUT /api/v1/books/{id}/analysis."""

    def test_create_analysis(self, client):
        """Test creating analysis for a book."""
        # Create a book
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Create analysis
        markdown_content = """# Book Analysis

## Executive Summary
This is a test analysis.

## Condition
Very good condition.
"""
        response = client.put(
            f"/api/v1/books/{book_id}/analysis",
            content=markdown_content,
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Analysis updated"

        # Verify it was created
        response = client.get(f"/api/v1/books/{book_id}/analysis/raw")
        assert response.status_code == 200
        assert "Executive Summary" in response.text

    def test_update_existing_analysis(self, client):
        """Test updating existing analysis."""
        # Create a book
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Create initial analysis
        client.put(
            f"/api/v1/books/{book_id}/analysis",
            content="# Initial Analysis",
            headers={"Content-Type": "text/plain"},
        )

        # Update analysis
        response = client.put(
            f"/api/v1/books/{book_id}/analysis",
            content="# Updated Analysis\n\nNew content here.",
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 200

        # Verify update
        response = client.get(f"/api/v1/books/{book_id}/analysis/raw")
        assert "Updated Analysis" in response.text
        assert "New content" in response.text

    def test_update_analysis_book_not_found(self, client):
        """Test 404 when book doesn't exist."""
        response = client.put(
            "/api/v1/books/999/analysis",
            content="# Test",
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 404


class TestPublisherIntegration:
    """Tests for publisher extraction and integration when saving analysis."""

    def test_publisher_from_structured_data_updates_book(self, client, db):
        """Test that publisher from structured data updates book.publisher_id."""
        # Create a book without publisher
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Verify no publisher initially
        response = client.get(f"/api/v1/books/{book_id}")
        assert response.json()["publisher"] is None

        # Upload analysis with publisher in structured data
        markdown_content = """---STRUCTURED-DATA---
PUBLISHER_IDENTIFIED: Harper & Brothers
PUBLISHER_CONFIDENCE: HIGH
---END-STRUCTURED-DATA---

## Executive Summary
A fine first edition published by Harper & Brothers.
"""
        response = client.put(
            f"/api/v1/books/{book_id}/analysis",
            content=markdown_content,
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 200
        assert response.json()["publisher_updated"] is True

        # Verify publisher was associated with book
        response = client.get(f"/api/v1/books/{book_id}")
        book_data = response.json()
        assert book_data["publisher"] is not None
        assert book_data["publisher"]["name"] == "Harper & Brothers"
        assert book_data["publisher"]["tier"] == "TIER_1"  # Known publisher

    def test_publisher_from_text_pattern_updates_book(self, client, db):
        """Test that publisher from **Publisher:** pattern updates book."""
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        markdown_content = """## Executive Summary
A Victorian binding in fine condition.

## II. PHYSICAL DESCRIPTION

**Publisher:** Macmillan and Co., London
**Binding:** Full Morocco
"""
        response = client.put(
            f"/api/v1/books/{book_id}/analysis",
            content=markdown_content,
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 200
        assert response.json()["publisher_updated"] is True

        response = client.get(f"/api/v1/books/{book_id}")
        book_data = response.json()
        assert book_data["publisher"] is not None
        # Location suffix should be auto-corrected
        assert book_data["publisher"]["name"] == "Macmillan and Co."
        assert book_data["publisher"]["tier"] == "TIER_1"

    def test_publisher_not_updated_when_already_set(self, client, db):
        """Test that publisher is not overwritten if already set to same."""
        from app.models.publisher import Publisher

        # Create publisher first
        publisher = Publisher(name="Oxford University Press", tier="TIER_1")
        db.add(publisher)
        db.flush()

        # Create book with publisher
        response = client.post(
            "/api/v1/books", json={"title": "Test Book", "publisher_id": publisher.id}
        )
        book_id = response.json()["id"]

        # Upload analysis with same publisher
        markdown_content = """---STRUCTURED-DATA---
PUBLISHER_IDENTIFIED: Oxford University Press
PUBLISHER_CONFIDENCE: HIGH
---END-STRUCTURED-DATA---
"""
        response = client.put(
            f"/api/v1/books/{book_id}/analysis",
            content=markdown_content,
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 200
        # Should be False since publisher is already the same
        assert response.json()["publisher_updated"] is False


class TestAnalysisWithBookInfo:
    """Tests for analysis info in book responses."""

    def test_book_has_analysis_flag(self, client):
        """Test has_analysis flag in book response."""
        # Create a book
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Initially no analysis
        response = client.get(f"/api/v1/books/{book_id}")
        assert response.json()["has_analysis"] is False

        # Add analysis
        client.put(
            f"/api/v1/books/{book_id}/analysis",
            content="# Test Analysis",
            headers={"Content-Type": "text/plain"},
        )

        # Now has analysis
        response = client.get(f"/api/v1/books/{book_id}")
        assert response.json()["has_analysis"] is True
