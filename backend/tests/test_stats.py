"""Statistics API tests."""

from freezegun import freeze_time


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

    @freeze_time("2025-06-15")
    def test_overview_week_delta_counts(self, client):
        """Test week_delta.count only counts books purchased in last 7 days.

        Issue #807: Verify week-over-week count calculation.
        """
        # Book purchased 3 days ago - should be counted
        client.post(
            "/api/v1/books",
            json={
                "title": "Recent Book 1",
                "inventory_type": "PRIMARY",
                "status": "ON_HAND",
                "purchase_date": "2025-06-12",  # 3 days ago
            },
        )
        # Book purchased 6 days ago - should be counted (within 7 days)
        client.post(
            "/api/v1/books",
            json={
                "title": "Recent Book 2",
                "inventory_type": "PRIMARY",
                "status": "ON_HAND",
                "purchase_date": "2025-06-09",  # 6 days ago
            },
        )
        # Book purchased exactly 7 days ago - should be counted (>= boundary)
        client.post(
            "/api/v1/books",
            json={
                "title": "Boundary Book",
                "inventory_type": "PRIMARY",
                "status": "ON_HAND",
                "purchase_date": "2025-06-08",  # exactly 7 days ago
            },
        )
        # Book purchased 10 days ago - should NOT be counted
        client.post(
            "/api/v1/books",
            json={
                "title": "Old Book",
                "inventory_type": "PRIMARY",
                "status": "ON_HAND",
                "purchase_date": "2025-06-05",  # 10 days ago
            },
        )
        # Book with no purchase_date - should NOT be counted
        client.post(
            "/api/v1/books",
            json={
                "title": "No Date Book",
                "inventory_type": "PRIMARY",
                "status": "ON_HAND",
            },
        )
        # Recent book but EXTENDED inventory type - should NOT be counted
        client.post(
            "/api/v1/books",
            json={
                "title": "Extended Book",
                "inventory_type": "EXTENDED",
                "purchase_date": "2025-06-14",
            },
        )
        # Recent book but IN_TRANSIT status - should NOT be counted
        client.post(
            "/api/v1/books",
            json={
                "title": "In Transit Book",
                "inventory_type": "PRIMARY",
                "status": "IN_TRANSIT",
                "purchase_date": "2025-06-14",
            },
        )

        response = client.get("/api/v1/stats/overview")
        assert response.status_code == 200
        data = response.json()

        # Only 3 books should be in week_delta: Recent Book 1, Recent Book 2, Boundary Book
        assert data["week_delta"]["count"] == 3

    @freeze_time("2025-06-15")
    def test_overview_week_delta_volumes(self, client):
        """Test week_delta.volumes sums volumes correctly, defaulting NULL to 1.

        Issue #807: Verify volume sum calculation handles multi-volume sets.
        """
        # Book with 5 volumes purchased recently
        client.post(
            "/api/v1/books",
            json={
                "title": "Multi-volume Set",
                "inventory_type": "PRIMARY",
                "status": "ON_HAND",
                "purchase_date": "2025-06-12",
                "volumes": 5,
            },
        )
        # Book with default volumes (1) purchased recently
        client.post(
            "/api/v1/books",
            json={
                "title": "Single Volume",
                "inventory_type": "PRIMARY",
                "status": "ON_HAND",
                "purchase_date": "2025-06-13",
                "volumes": 1,
            },
        )
        # Book with NULL volumes (should default to 1)
        client.post(
            "/api/v1/books",
            json={
                "title": "No Volumes Specified",
                "inventory_type": "PRIMARY",
                "status": "ON_HAND",
                "purchase_date": "2025-06-14",
            },
        )
        # Old book with many volumes - should NOT be included
        client.post(
            "/api/v1/books",
            json={
                "title": "Old Multi-volume",
                "inventory_type": "PRIMARY",
                "status": "ON_HAND",
                "purchase_date": "2025-06-01",  # 14 days ago
                "volumes": 24,
            },
        )

        response = client.get("/api/v1/stats/overview")
        assert response.status_code == 200
        data = response.json()

        # week_delta.volumes should be 5 + 1 + 1 = 7
        assert data["week_delta"]["volumes"] == 7

    @freeze_time("2025-06-15")
    def test_overview_week_delta_value(self, client):
        """Test week_delta.value_mid is sum of recent book values.

        Issue #807: Verify value sum calculation.
        """
        # Book with value purchased recently
        client.post(
            "/api/v1/books",
            json={
                "title": "Valuable Book",
                "inventory_type": "PRIMARY",
                "status": "ON_HAND",
                "purchase_date": "2025-06-12",
                "value_mid": 500.50,
            },
        )
        # Another valuable book
        client.post(
            "/api/v1/books",
            json={
                "title": "Another Valuable",
                "inventory_type": "PRIMARY",
                "status": "ON_HAND",
                "purchase_date": "2025-06-13",
                "value_mid": 250.25,
            },
        )
        # Book with no value (NULL) - should contribute 0
        client.post(
            "/api/v1/books",
            json={
                "title": "No Value Book",
                "inventory_type": "PRIMARY",
                "status": "ON_HAND",
                "purchase_date": "2025-06-14",
            },
        )
        # Old valuable book - should NOT be included
        client.post(
            "/api/v1/books",
            json={
                "title": "Old Valuable",
                "inventory_type": "PRIMARY",
                "status": "ON_HAND",
                "purchase_date": "2025-06-01",  # 14 days ago
                "value_mid": 10000,
            },
        )

        response = client.get("/api/v1/stats/overview")
        assert response.status_code == 200
        data = response.json()

        # week_delta.value_mid should be 500.50 + 250.25 + 0 = 750.75
        assert data["week_delta"]["value_mid"] == 750.75

    @freeze_time("2025-06-15")
    def test_overview_week_delta_authenticated(self, client, db):
        """Test week_delta.authenticated_bindings counts authenticated books.

        Issue #807: Verify authenticated binding count for recent acquisitions.
        """
        from app.models import Binder

        # Create a binder for the authenticated books
        binder = Binder(name="Zaehnsdorf", full_name="Joseph Zaehnsdorf")
        db.add(binder)
        db.commit()

        # Authenticated binding book purchased recently
        client.post(
            "/api/v1/books",
            json={
                "title": "Authenticated Recent",
                "inventory_type": "PRIMARY",
                "status": "ON_HAND",
                "purchase_date": "2025-06-12",
                "binder_id": binder.id,
                "binding_authenticated": True,
            },
        )
        # Another authenticated binding book
        client.post(
            "/api/v1/books",
            json={
                "title": "Another Authenticated",
                "inventory_type": "PRIMARY",
                "status": "ON_HAND",
                "purchase_date": "2025-06-13",
                "binder_id": binder.id,
                "binding_authenticated": True,
            },
        )
        # Non-authenticated binding book purchased recently
        client.post(
            "/api/v1/books",
            json={
                "title": "Not Authenticated",
                "inventory_type": "PRIMARY",
                "status": "ON_HAND",
                "purchase_date": "2025-06-14",
                "binding_authenticated": False,
            },
        )
        # Old authenticated book - should NOT be included
        client.post(
            "/api/v1/books",
            json={
                "title": "Old Authenticated",
                "inventory_type": "PRIMARY",
                "status": "ON_HAND",
                "purchase_date": "2025-06-01",  # 14 days ago
                "binder_id": binder.id,
                "binding_authenticated": True,
            },
        )

        response = client.get("/api/v1/stats/overview")
        assert response.status_code == 200
        data = response.json()

        # week_delta.authenticated_bindings should be 2
        assert data["week_delta"]["authenticated_bindings"] == 2


class TestStatsMetrics:
    """Tests for GET /api/v1/stats/metrics."""

    def test_metrics_empty(self, client):
        """Test metrics with empty database."""
        response = client.get("/api/v1/stats/metrics")
        assert response.status_code == 200
        data = response.json()
        # When empty, API returns zeros for all metrics
        assert "victorian_percentage" in data or data.get("total_items", 0) == 0

    def test_metrics_victorian_percentage(self, client):
        """Test Victorian percentage calculation based on year_start.

        The implementation considers books Victorian if year_start or year_end
        is between 1800-1901 (inclusive).
        """
        # Create 4 books: 2 Victorian (1850, 1880), 2 non-Victorian (1750, 1920)
        client.post(
            "/api/v1/books",
            json={
                "title": "Victorian Book 1",
                "publication_date": "1850",
                "inventory_type": "PRIMARY",
            },
        )
        client.post(
            "/api/v1/books",
            json={
                "title": "Victorian Book 2",
                "publication_date": "1880",
                "inventory_type": "PRIMARY",
            },
        )
        client.post(
            "/api/v1/books",
            json={
                "title": "Pre-Victorian Book",
                "publication_date": "1750",
                "inventory_type": "PRIMARY",
            },
        )
        client.post(
            "/api/v1/books",
            json={
                "title": "Post-Victorian Book",
                "publication_date": "1920",
                "inventory_type": "PRIMARY",
            },
        )

        response = client.get("/api/v1/stats/metrics")
        assert response.status_code == 200
        data = response.json()
        # 2 out of 4 books are Victorian = 50%
        assert data["victorian_percentage"] == 50.0
        assert data["total_items"] == 4

    def test_metrics_victorian_year_end_fallback(self, client, db):
        """Test year_end fallback when year_start is None.

        When year_start is None but year_end is in Victorian range (1800-1901),
        the book should be counted as Victorian.
        """
        from app.models import Book

        # Create a book directly with only year_end set (Victorian era)
        book_victorian = Book(
            title="Only Year End Book",
            inventory_type="PRIMARY",
            year_start=None,
            year_end=1880,
        )
        db.add(book_victorian)
        db.commit()

        # Create a non-Victorian book for comparison
        book_modern = Book(
            title="Modern Book",
            inventory_type="PRIMARY",
            year_start=1950,
            year_end=None,
        )
        db.add(book_modern)
        db.commit()

        response = client.get("/api/v1/stats/metrics")
        assert response.status_code == 200
        data = response.json()

        # 1 out of 2 books is Victorian (via year_end fallback) = 50%
        assert data["total_items"] == 2
        assert data["victorian_percentage"] == 50.0

    def test_metrics_average_discount_and_roi(self, client):
        """Test average discount and ROI calculations.

        Average should only include books that have the field set (not None).
        """
        # Create books with various discount/ROI values
        client.post(
            "/api/v1/books",
            json={
                "title": "Book 1",
                "inventory_type": "PRIMARY",
                "discount_pct": 20.0,
                "roi_pct": 50.0,
            },
        )
        client.post(
            "/api/v1/books",
            json={
                "title": "Book 2",
                "inventory_type": "PRIMARY",
                "discount_pct": 30.0,
                "roi_pct": 100.0,
            },
        )
        # Book without discount/ROI - should not affect averages
        client.post(
            "/api/v1/books",
            json={
                "title": "Book 3",
                "inventory_type": "PRIMARY",
            },
        )

        response = client.get("/api/v1/stats/metrics")
        assert response.status_code == 200
        data = response.json()

        # Average of 20 and 30 = 25
        assert data["average_discount"] == 25.0
        # Average of 50 and 100 = 75
        assert data["average_roi"] == 75.0
        assert data["total_items"] == 3

    def test_metrics_totals(self, client):
        """Test total_purchase_cost and total_current_value calculations."""
        client.post(
            "/api/v1/books",
            json={
                "title": "Book 1",
                "inventory_type": "PRIMARY",
                "purchase_price": 100.50,
                "value_mid": 200.00,
            },
        )
        client.post(
            "/api/v1/books",
            json={
                "title": "Book 2",
                "inventory_type": "PRIMARY",
                "purchase_price": 50.25,
                "value_mid": 150.75,
            },
        )
        # Book without prices - should contribute 0 to totals
        client.post(
            "/api/v1/books",
            json={
                "title": "Book 3",
                "inventory_type": "PRIMARY",
            },
        )

        response = client.get("/api/v1/stats/metrics")
        assert response.status_code == 200
        data = response.json()

        # 100.50 + 50.25 = 150.75
        assert data["total_purchase_cost"] == 150.75
        # 200.00 + 150.75 = 350.75
        assert data["total_current_value"] == 350.75
        assert data["total_items"] == 3


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

    def test_by_era_pre_romantic(self, client):
        """Test Pre-Romantic era classification for 18th century books.

        Issue #807: Books from before 1800 (e.g., 1750) should be classified as
        "Pre-Romantic (before 1800)", not incorrectly placed in "Post-1910".
        """
        response = client.post(
            "/api/v1/books",
            json={
                "title": "18th Century Book",
                "publication_date": "1750",
                "value_mid": 500,
                "inventory_type": "PRIMARY",
            },
        )
        assert response.status_code == 201, response.json()

        response = client.get("/api/v1/stats/by-era")
        assert response.status_code == 200
        data = response.json()

        # Should find Pre-Romantic category for 1750 book
        pre_romantic = next((e for e in data if "Pre-Romantic" in e["era"]), None)
        assert pre_romantic is not None, (
            f"Pre-Romantic era not found in {data}. "
            "Books from before 1800 should be categorized as Pre-Romantic."
        )
        assert pre_romantic["count"] == 1
        assert pre_romantic["value"] == 500

    def test_by_era_all_categories(self, client):
        """Test all era categories are correctly classified.

        Creates books spanning all eras to verify each gets the correct category.
        """
        # Create books for each era
        books = [
            ("Pre-Romantic Book", "1750", 100),  # Pre-Romantic (before 1800)
            ("Romantic Book", "1820", 200),  # Romantic (1800-1837)
            ("Victorian Book", "1870", 300),  # Victorian (1837-1901)
            ("Edwardian Book", "1905", 400),  # Edwardian (1901-1910)
            ("Modern Book", "1920", 500),  # Post-1910
        ]

        for title, year, value in books:
            response = client.post(
                "/api/v1/books",
                json={
                    "title": title,
                    "publication_date": year,
                    "value_mid": value,
                    "inventory_type": "PRIMARY",
                },
            )
            assert response.status_code == 201, f"Failed to create {title}: {response.json()}"

        response = client.get("/api/v1/stats/by-era")
        assert response.status_code == 200
        data = response.json()

        # Verify each era has exactly one book
        expected_eras = {
            "Pre-Romantic": {"count": 1, "value": 100},
            "Romantic": {"count": 1, "value": 200},
            "Victorian": {"count": 1, "value": 300},
            "Edwardian": {"count": 1, "value": 400},
            "Post-1910": {"count": 1, "value": 500},
        }

        for era_prefix, expected in expected_eras.items():
            # Use startswith to avoid "Romantic" matching "Pre-Romantic"
            era_data = next((e for e in data if e["era"].startswith(era_prefix)), None)
            assert era_data is not None, f"{era_prefix} era not found in {data}"
            assert era_data["count"] == expected["count"], (
                f"{era_prefix} count mismatch: expected {expected['count']}, got {era_data['count']}"
            )
            assert era_data["value"] == expected["value"], (
                f"{era_prefix} value mismatch: expected {expected['value']}, got {era_data['value']}"
            )

    def test_by_era_uses_year_end_fallback(self, client, db):
        """Test era classification uses year_end when year_start is None.

        When a book has no year_start but has a year_end, the era classification
        should use year_end as the fallback.
        """
        from app.models import Book

        # Create book directly in DB to set year_start=None, year_end=1850
        # (API might auto-populate year_start from publication_date)
        book = Book(
            title="Book with only year_end",
            year_start=None,
            year_end=1850,
            value_mid=250,
            inventory_type="PRIMARY",
        )
        db.add(book)
        db.commit()

        response = client.get("/api/v1/stats/by-era")
        assert response.status_code == 200
        data = response.json()

        # Book with year_end=1850 should be classified as Victorian
        victorian = next((e for e in data if "Victorian" in e["era"]), None)
        assert victorian is not None, f"Victorian era not found in {data}"
        assert victorian["count"] == 1
        assert victorian["value"] == 250


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

    def test_by_author_count_is_records_total_volumes_is_sum(self, client, db):
        """Test that count is record count, total_volumes is sum of volumes.

        Issue #827: count was incorrectly returning sum of volumes.
        A 24-volume encyclopedia should return count: 1, total_volumes: 24.
        """
        from app.models import Author

        author = Author(name="Charles Dickens")
        db.add(author)
        db.commit()

        # Create 2 book records: one 24-volume set and one 1-volume book
        client.post(
            "/api/v1/books",
            json={
                "title": "Works of Dickens",
                "author_id": author.id,
                "volumes": 24,
                "value_mid": 1000,
            },
        )
        client.post(
            "/api/v1/books",
            json={
                "title": "A Christmas Carol",
                "author_id": author.id,
                "volumes": 1,
                "value_mid": 100,
            },
        )

        response = client.get("/api/v1/stats/by-author")
        assert response.status_code == 200
        data = response.json()

        dickens = next((a for a in data if a["author"] == "Charles Dickens"), None)
        assert dickens is not None
        # count should be number of book records (2), NOT sum of volumes
        assert dickens["count"] == 2, "count should be record count, not volume sum"
        # total_volumes should be the sum of volumes (24 + 1 = 25)
        assert dickens["total_volumes"] == 25, "total_volumes should be sum of volumes"
        assert dickens["titles"] == 2  # 2 distinct titles
        assert len(dickens["sample_titles"]) == 2

    def test_by_author_sample_titles_limit(self, client, db):
        """Test that sample_titles contains at most 5 titles.

        Issue #807: Performance optimization - sample_titles should be limited
        to 5 books to avoid excessive data transfer.
        """
        from app.models import Author

        author = Author(name="Prolific Author")
        db.add(author)
        db.commit()

        # Create 10 books for this author
        for i in range(10):
            client.post(
                "/api/v1/books",
                json={
                    "title": f"Book Number {i + 1}",
                    "author_id": author.id,
                    "value_mid": 100,
                },
            )

        response = client.get("/api/v1/stats/by-author")
        assert response.status_code == 200
        data = response.json()

        prolific = next((a for a in data if a["author"] == "Prolific Author"), None)
        assert prolific is not None
        assert prolific["count"] == 10, "Should have 10 book records"
        # sample_titles should be limited to 5
        assert len(prolific["sample_titles"]) <= 5, "sample_titles should contain at most 5 titles"

    def test_by_author_has_more_flag(self, client, db):
        """Test that has_more flag correctly indicates if more books exist.

        Issue #807: has_more should be True when author has more than 5 books,
        False when 5 or fewer.
        """
        from app.models import Author

        # Author with 6 books (has_more should be True)
        author_many = Author(name="Many Books Author")
        db.add(author_many)
        db.commit()

        for i in range(6):
            client.post(
                "/api/v1/books",
                json={
                    "title": f"Many Book {i + 1}",
                    "author_id": author_many.id,
                    "value_mid": 100,
                },
            )

        # Author with 3 books (has_more should be False)
        author_few = Author(name="Few Books Author")
        db.add(author_few)
        db.commit()

        for i in range(3):
            client.post(
                "/api/v1/books",
                json={
                    "title": f"Few Book {i + 1}",
                    "author_id": author_few.id,
                    "value_mid": 100,
                },
            )

        response = client.get("/api/v1/stats/by-author")
        assert response.status_code == 200
        data = response.json()

        many = next((a for a in data if a["author"] == "Many Books Author"), None)
        assert many is not None
        assert many["has_more"] is True, "has_more should be True when author has more than 5 books"

        few = next((a for a in data if a["author"] == "Few Books Author"), None)
        assert few is not None
        assert few["has_more"] is False, "has_more should be False when author has 5 or fewer books"

    def test_by_author_multiple_authors_sample_titles(self, client, db):
        """Test that sample_titles works correctly for multiple authors.

        Issue #807: This tests the batch query approach - verifying that
        sample_titles are correctly associated with each author when
        fetching data for multiple authors at once.
        """
        from app.models import Author

        # Create first author with specific titles
        author1 = Author(name="Author One")
        db.add(author1)
        db.commit()

        author1_titles = ["Alpha Book", "Beta Book", "Gamma Book"]
        for title in author1_titles:
            client.post(
                "/api/v1/books",
                json={
                    "title": title,
                    "author_id": author1.id,
                    "value_mid": 100,
                },
            )

        # Create second author with different titles
        author2 = Author(name="Author Two")
        db.add(author2)
        db.commit()

        author2_titles = ["Delta Book", "Epsilon Book"]
        for title in author2_titles:
            client.post(
                "/api/v1/books",
                json={
                    "title": title,
                    "author_id": author2.id,
                    "value_mid": 200,
                },
            )

        response = client.get("/api/v1/stats/by-author")
        assert response.status_code == 200
        data = response.json()

        # Verify Author One has correct sample_titles
        a1 = next((a for a in data if a["author"] == "Author One"), None)
        assert a1 is not None
        assert a1["count"] == 3
        assert len(a1["sample_titles"]) == 3
        # All of author1's titles should be in the sample
        for title in author1_titles:
            assert title in a1["sample_titles"], (
                f"'{title}' should be in Author One's sample_titles"
            )
        # None of author2's titles should be in author1's sample
        for title in author2_titles:
            assert title not in a1["sample_titles"], (
                f"'{title}' should NOT be in Author One's sample_titles"
            )

        # Verify Author Two has correct sample_titles
        a2 = next((a for a in data if a["author"] == "Author Two"), None)
        assert a2 is not None
        assert a2["count"] == 2
        assert len(a2["sample_titles"]) == 2
        # All of author2's titles should be in the sample
        for title in author2_titles:
            assert title in a2["sample_titles"], (
                f"'{title}' should be in Author Two's sample_titles"
            )
        # None of author1's titles should be in author2's sample
        for title in author1_titles:
            assert title not in a2["sample_titles"], (
                f"'{title}' should NOT be in Author Two's sample_titles"
            )


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


class TestSecurityEndpoints:
    """Tests for endpoint security - issue #804."""

    def test_fix_publisher_tiers_endpoint_removed(self, client):
        """Verify /fix-publisher-tiers endpoint was removed (security fix #804).

        This endpoint was an unauthenticated one-time migration that should
        never have been a permanent API endpoint.
        """
        response = client.post("/api/v1/stats/fix-publisher-tiers")
        assert response.status_code == 404, (
            "fix-publisher-tiers endpoint should be removed - it was an "
            "unauthenticated endpoint that could modify the database"
        )
