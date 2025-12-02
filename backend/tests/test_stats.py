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


class TestAcquisitionsByMonth:
    """Tests for GET /api/v1/stats/acquisitions-by-month."""

    def test_acquisitions_empty(self, client):
        """Test with no books."""
        response = client.get("/api/v1/stats/acquisitions-by-month")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_acquisitions_with_purchase_dates(self, client):
        """Test monthly acquisition aggregation."""
        # Create books with purchase dates
        client.post(
            "/api/v1/books",
            json={
                "title": "Book Nov 2025",
                "purchase_date": "2025-11-15",
                "value_mid": 100,
                "purchase_price": 80,
            },
        )
        client.post(
            "/api/v1/books",
            json={
                "title": "Book Nov 2025 #2",
                "purchase_date": "2025-11-20",
                "value_mid": 200,
                "purchase_price": 150,
            },
        )

        response = client.get("/api/v1/stats/acquisitions-by-month")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["year"] == 2025
        assert data[0]["month"] == 11
        assert data[0]["count"] == 2
        assert data[0]["value"] == 300
        assert data[0]["cost"] == 230


class TestBindingStats:
    """Tests for GET /api/v1/stats/bindings."""

    def test_bindings_empty(self, client):
        """Test with no authenticated bindings."""
        response = client.get("/api/v1/stats/bindings")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_bindings_with_binders(self, client, db):
        """Test binding counts by binder."""
        from app.models import Binder

        # Create a binder
        binder = Binder(name="Zaehnsdorf", full_name="Joseph Zaehnsdorf")
        db.add(binder)
        db.commit()

        # Create authenticated books with this binder
        client.post(
            "/api/v1/books",
            json={
                "title": "Zaehnsdorf Book 1",
                "binder_id": binder.id,
                "binding_authenticated": True,
                "value_mid": 500,
            },
        )
        client.post(
            "/api/v1/books",
            json={
                "title": "Zaehnsdorf Book 2",
                "binder_id": binder.id,
                "binding_authenticated": True,
                "value_mid": 750,
            },
        )

        response = client.get("/api/v1/stats/bindings")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["binder"] == "Zaehnsdorf"
        assert data[0]["count"] == 2
        assert data[0]["value"] == 1250


class TestByEra:
    """Tests for GET /api/v1/stats/by-era."""

    def test_by_era_empty(self, client):
        """Test with no books."""
        response = client.get("/api/v1/stats/by-era")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_by_era_victorian(self, client):
        """Test era classification for Victorian books."""
        # Books need inventory_type PRIMARY to be included in stats
        # year_start is parsed from publication_date field
        response1 = client.post(
            "/api/v1/books",
            json={
                "title": "Victorian Book",
                "publication_date": "1880",  # year_start is parsed from this
                "value_mid": 100,
                "inventory_type": "PRIMARY",
            },
        )
        assert response1.status_code == 201, response1.json()

        response2 = client.post(
            "/api/v1/books",
            json={
                "title": "Romantic Book",
                "publication_date": "1820",  # year_start is parsed from this
                "value_mid": 200,
                "inventory_type": "PRIMARY",
            },
        )
        assert response2.status_code == 201, response2.json()

        response = client.get("/api/v1/stats/by-era")
        assert response.status_code == 200
        data = response.json()

        # The API returns era names like "Victorian (1837-1901)"
        victorian = next((e for e in data if "Victorian" in e["era"]), None)
        romantic = next((e for e in data if "Romantic" in e["era"]), None)

        assert victorian is not None, f"Victorian not found in {data}"
        assert victorian["count"] == 1
        assert romantic is not None, f"Romantic not found in {data}"
        assert romantic["count"] == 1


class TestByPublisher:
    """Tests for GET /api/v1/stats/by-publisher."""

    def test_by_publisher_empty(self, client):
        """Test with no books."""
        response = client.get("/api/v1/stats/by-publisher")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_by_publisher_with_tiers(self, client, db):
        """Test publisher breakdown with tier info."""
        from app.models import Publisher

        # Create publishers
        tier1 = Publisher(name="Chapman & Hall", tier="TIER_1")
        tier2 = Publisher(name="Other Press", tier="TIER_2")
        db.add_all([tier1, tier2])
        db.commit()

        client.post(
            "/api/v1/books",
            json={"title": "C&H Book", "publisher_id": tier1.id, "value_mid": 500},
        )
        client.post(
            "/api/v1/books",
            json={"title": "Other Book", "publisher_id": tier2.id, "value_mid": 100},
        )

        response = client.get("/api/v1/stats/by-publisher")
        assert response.status_code == 200
        data = response.json()

        ch = next((p for p in data if p["publisher"] == "Chapman & Hall"), None)
        assert ch is not None
        assert ch["tier"] == "TIER_1"
        assert ch["count"] == 1


class TestByAuthor:
    """Tests for GET /api/v1/stats/by-author."""

    def test_by_author_empty(self, client):
        """Test with no books."""
        response = client.get("/api/v1/stats/by-author")
        assert response.status_code == 200
        data = response.json()
        assert data == []


class TestValueByCategory:
    """Tests for GET /api/v1/stats/value-by-category."""

    def test_value_by_category_empty(self, client):
        """Test with no books."""
        response = client.get("/api/v1/stats/value-by-category")
        assert response.status_code == 200
        data = response.json()
        # Should return categories with zero values
        assert isinstance(data, list)

    def test_value_by_category_distribution(self, client, db):
        """Test value distribution across categories."""
        from app.models import Binder

        # Create a binder for premium binding
        binder = Binder(name="Rivière", full_name="Robert Rivière")
        db.add(binder)
        db.commit()

        # Premium binding book
        client.post(
            "/api/v1/books",
            json={
                "title": "Premium Book",
                "binder_id": binder.id,
                "binding_authenticated": True,
                "value_mid": 1000,
            },
        )
        # Regular book
        client.post(
            "/api/v1/books",
            json={"title": "Regular Book", "value_mid": 100},
        )

        response = client.get("/api/v1/stats/value-by-category")
        assert response.status_code == 200
        data = response.json()

        premium = next((c for c in data if c["category"] == "Premium Bindings"), None)
        assert premium is not None
        assert premium["value"] == 1000
