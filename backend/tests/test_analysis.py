"""Analysis API tests."""


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
            params={"full_markdown": markdown_content},
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
            params={"full_markdown": "# Initial Analysis"},
        )

        # Update analysis
        response = client.put(
            f"/api/v1/books/{book_id}/analysis",
            params={"full_markdown": "# Updated Analysis\n\nNew content here."},
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
            params={"full_markdown": "# Test"},
        )
        assert response.status_code == 404


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
            params={"full_markdown": "# Test Analysis"},
        )

        # Now has analysis
        response = client.get(f"/api/v1/books/{book_id}")
        assert response.json()["has_analysis"] is True
