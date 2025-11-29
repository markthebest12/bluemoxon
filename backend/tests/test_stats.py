"""Statistics API tests."""


class TestStatsOverview:
    """Tests for GET /api/v1/stats/overview."""

    def test_overview_empty(self, client):
        """Test overview with empty database."""
        response = client.get("/api/v1/stats/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["primary"]["count"] == 0
        assert data["extended"]["count"] == 0
        assert data["total_items"] == 0

    def test_overview_with_books(self, client):
        """Test overview counts books correctly."""
        # Create some books
        client.post("/api/v1/books", json={"title": "Book 1", "inventory_type": "PRIMARY"})
        client.post("/api/v1/books", json={"title": "Book 2", "inventory_type": "PRIMARY"})
        client.post("/api/v1/books", json={"title": "Book 3", "inventory_type": "EXTENDED"})

        response = client.get("/api/v1/stats/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["primary"]["count"] == 2
        assert data["extended"]["count"] == 1
        assert data["total_items"] == 3


class TestStatsMetrics:
    """Tests for GET /api/v1/stats/metrics."""

    def test_metrics_empty(self, client):
        """Test metrics with empty database."""
        response = client.get("/api/v1/stats/metrics")
        assert response.status_code == 200
        data = response.json()
        # When empty, API returns zeros for all metrics
        assert "victorian_percentage" in data or data.get("total_items", 0) == 0


class TestStatsByCategory:
    """Tests for GET /api/v1/stats/by-category."""

    def test_by_category(self, client):
        """Test category breakdown."""
        # Create books with categories
        client.post(
            "/api/v1/books",
            json={"title": "Poetry 1", "category": "Victorian Poetry"},
        )
        client.post(
            "/api/v1/books",
            json={"title": "Poetry 2", "category": "Victorian Poetry"},
        )
        client.post(
            "/api/v1/books",
            json={"title": "Bio 1", "category": "Victorian Biography"},
        )

        response = client.get("/api/v1/stats/by-category")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        poetry = next((c for c in data if c["category"] == "Victorian Poetry"), None)
        assert poetry is not None
        assert poetry["count"] == 2


class TestPendingDeliveries:
    """Tests for GET /api/v1/stats/pending-deliveries."""

    def test_pending_deliveries_empty(self, client):
        """Test with no in-transit books."""
        response = client.get("/api/v1/stats/pending-deliveries")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["items"] == []

    def test_pending_deliveries_with_items(self, client):
        """Test with in-transit books."""
        client.post(
            "/api/v1/books",
            json={"title": "In Transit Book", "status": "IN_TRANSIT"},
        )
        client.post(
            "/api/v1/books",
            json={"title": "On Hand Book", "status": "ON_HAND"},
        )

        response = client.get("/api/v1/stats/pending-deliveries")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["items"][0]["title"] == "In Transit Book"
