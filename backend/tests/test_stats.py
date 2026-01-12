"""Statistics API tests."""

import json

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


class TestStatsByCondition:
    """Tests for GET /api/v1/stats/by-condition."""

    def test_by_condition_empty(self, client):
        """Test with no books returns empty list."""
        response = client.get("/api/v1/stats/by-condition")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_by_condition_groups_by_grade(self, client):
        """Test condition breakdown groups by grade."""
        # Create books with different condition grades
        client.post(
            "/api/v1/books",
            json={"title": "Fine Book 1", "condition_grade": "FINE", "value_mid": 100},
        )
        client.post(
            "/api/v1/books",
            json={"title": "Fine Book 2", "condition_grade": "FINE", "value_mid": 200},
        )
        client.post(
            "/api/v1/books",
            json={"title": "Good Book", "condition_grade": "GOOD", "value_mid": 50},
        )

        response = client.get("/api/v1/stats/by-condition")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        fine = next((c for c in data if c["condition"] == "FINE"), None)
        assert fine is not None
        assert fine["count"] == 2
        assert fine["value"] == 300

        good = next((c for c in data if c["condition"] == "GOOD"), None)
        assert good is not None
        assert good["count"] == 1
        assert good["value"] == 50

    def test_by_condition_null_becomes_ungraded(self, client):
        """Test null condition_grade shows as 'Ungraded'."""
        client.post(
            "/api/v1/books",
            json={"title": "No Condition Book", "value_mid": 75},
        )

        response = client.get("/api/v1/stats/by-condition")
        assert response.status_code == 200
        data = response.json()

        ungraded = next((c for c in data if c["condition"] == "Ungraded"), None)
        assert ungraded is not None
        assert ungraded["count"] == 1
        assert ungraded["value"] == 75

    def test_by_condition_includes_value(self, client):
        """Test response includes value sum for each condition."""
        client.post(
            "/api/v1/books",
            json={"title": "VG Book 1", "condition_grade": "VERY_GOOD", "value_mid": 100.50},
        )
        client.post(
            "/api/v1/books",
            json={"title": "VG Book 2", "condition_grade": "VERY_GOOD", "value_mid": 50.25},
        )

        response = client.get("/api/v1/stats/by-condition")
        assert response.status_code == 200
        data = response.json()

        vg = next((c for c in data if c["condition"] == "VERY_GOOD"), None)
        assert vg is not None
        assert vg["value"] == 150.75


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

    def test_by_author_count_is_volumes_titles_is_records(self, client, db):
        """Test that count is total volumes, titles is record count.

        The chart displays total volumes per author (a 24-volume set counts as 24).
        The 'titles' field shows number of distinct book records.
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
        # count should be total volumes (24 + 1 = 25) - this is what the chart displays
        assert dickens["count"] == 25, "count should be total volumes for chart display"
        # total_volumes is the same as count for backward compatibility
        assert dickens["total_volumes"] == 25, "total_volumes should be sum of volumes"
        # titles should be number of book records (2)
        assert dickens["titles"] == 2, "titles should be number of distinct book records"
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


class TestDashboardBatch:
    """Tests for GET /api/v1/stats/dashboard batch endpoint."""

    def test_dashboard_returns_all_sections(self, client, db):
        """Test that dashboard returns all required data sections."""
        from app.models import Author, Binder, Publisher

        # Create reference data
        author = Author(name="Charles Dickens")
        binder = Binder(name="Zaehnsdorf", full_name="Joseph Zaehnsdorf")
        publisher = Publisher(name="Chapman & Hall", tier="TIER_1")
        db.add_all([author, binder, publisher])
        db.commit()

        # Create a book with all associations
        client.post(
            "/api/v1/books",
            json={
                "title": "A Christmas Carol",
                "author_id": author.id,
                "publisher_id": publisher.id,
                "binder_id": binder.id,
                "binding_authenticated": True,
                "publication_date": "1843",
                "inventory_type": "PRIMARY",
                "status": "ON_HAND",
                "purchase_date": "2026-01-01",
                "value_mid": 500,
            },
        )

        response = client.get("/api/v1/stats/dashboard")
        assert response.status_code == 200
        data = response.json()

        # Verify all sections exist
        assert "overview" in data
        assert "bindings" in data
        assert "by_era" in data
        assert "by_publisher" in data
        assert "by_author" in data
        assert "acquisitions_daily" in data

        # Verify overview structure
        assert "primary" in data["overview"]
        assert "week_delta" in data["overview"]

    def test_dashboard_accepts_query_params(self, client):
        """Test reference_date and days parameters."""
        response = client.get("/api/v1/stats/dashboard?reference_date=2026-01-06&days=14")
        assert response.status_code == 200
        data = response.json()
        # Should have 14 days of acquisition data
        assert len(data["acquisitions_daily"]) == 14

    def test_dashboard_empty_database(self, client):
        """Test dashboard with no books."""
        response = client.get("/api/v1/stats/dashboard")
        assert response.status_code == 200
        data = response.json()

        assert data["overview"]["primary"]["count"] == 0
        assert data["bindings"] == []
        assert data["by_era"] == []
        assert data["by_publisher"] == []
        assert data["by_author"] == []

    def test_dashboard_includes_condition_and_category(self, client):
        """Test dashboard batch includes by_condition and by_category."""
        client.post(
            "/api/v1/books",
            json={
                "title": "Test Book",
                "condition_grade": "FINE",
                "category": "Victorian Poetry",
            },
        )

        response = client.get("/api/v1/stats/dashboard")
        assert response.status_code == 200
        data = response.json()

        assert "by_condition" in data
        assert "by_category" in data

        # Verify data structure
        assert len(data["by_condition"]) >= 1
        fine = next((c for c in data["by_condition"] if c["condition"] == "FINE"), None)
        assert fine is not None
        assert fine["count"] == 1

        assert len(data["by_category"]) >= 1
        poetry = next((c for c in data["by_category"] if c["category"] == "Victorian Poetry"), None)
        assert poetry is not None
        assert poetry["count"] == 1


class TestStatsEdgeCases:
    """Tests for edge cases: Unicode, injection strings, boundary values.

    Issue #1004: Verify stats endpoints handle edge cases correctly.

    Note: condition_grade is validated against ConditionGrade enum on API input,
    but the database may contain legacy values. Tests that need non-standard
    condition grades create books directly in the database to simulate legacy data.
    """

    def test_condition_with_unicode_french(self, client, db):
        """Legacy condition grades with French Unicode render correctly in stats.

        The API validates against enum values, but legacy data might have
        non-standard grades. Stats should display them correctly.
        """
        from app.models import Book

        # Create directly in DB to simulate legacy data with non-standard grade
        book = Book(
            title="French Condition Book",
            condition_grade="très bien",
            value_mid=100,
            inventory_type="PRIMARY",
        )
        db.add(book)
        db.commit()

        response = client.get("/api/v1/stats/by-condition")
        assert response.status_code == 200
        data = response.json()

        french = next((c for c in data if c["condition"] == "très bien"), None)
        assert french is not None, f"Unicode condition 'très bien' not found in {data}"
        assert french["count"] == 1
        assert french["value"] == 100

    def test_condition_with_unicode_japanese(self, client, db):
        """Legacy condition grades with Japanese characters render correctly."""
        from app.models import Book

        book = Book(
            title="Japanese Condition Book",
            condition_grade="良好",
            value_mid=200,
            inventory_type="PRIMARY",
        )
        db.add(book)
        db.commit()

        response = client.get("/api/v1/stats/by-condition")
        assert response.status_code == 200
        data = response.json()

        japanese = next((c for c in data if c["condition"] == "良好"), None)
        assert japanese is not None, f"Unicode condition '良好' not found in {data}"
        assert japanese["count"] == 1
        assert japanese["value"] == 200

    def test_condition_with_emoji(self, client, db):
        """Legacy condition grades with emoji render correctly."""
        from app.models import Book

        emoji_condition = "📚 Fine"
        book = Book(
            title="Emoji Condition Book",
            condition_grade=emoji_condition,
            value_mid=150,
            inventory_type="PRIMARY",
        )
        db.add(book)
        db.commit()

        response = client.get("/api/v1/stats/by-condition")
        assert response.status_code == 200
        data = response.json()

        emoji = next((c for c in data if c["condition"] == emoji_condition), None)
        assert emoji is not None, f"Emoji condition '📚 Fine' not found in {data}"
        assert emoji["count"] == 1
        assert emoji["value"] == 150

    def test_condition_with_sql_injection_string(self, client, db):
        """SQL injection strings in condition_grade are returned as-is, not interpreted.

        Tests that SQLAlchemy properly parameterizes queries and the stats
        endpoint safely handles malicious strings in the database.

        Note: condition_grade is VARCHAR(20), so we use a shortened injection
        string that still demonstrates the security principle.
        """
        from app.models import Book

        # Shortened to fit VARCHAR(20): "1' OR '1'='1" is 12 chars
        injection_string = "1' OR '1'='1"
        book = Book(
            title="SQL Injection Test Book",
            condition_grade=injection_string,
            value_mid=100,
            inventory_type="PRIMARY",
        )
        db.add(book)
        db.commit()

        response = client.get("/api/v1/stats/by-condition")
        assert response.status_code == 200
        data = response.json()

        injection = next((c for c in data if c["condition"] == injection_string), None)
        assert injection is not None, (
            f"Injection string should be returned as-is: {injection_string}"
        )
        assert injection["count"] == 1
        assert injection["value"] == 100

        # Verify the database still works (table wasn't dropped)
        response2 = client.get("/api/v1/stats/overview")
        assert response2.status_code == 200
        assert response2.json()["total_items"] >= 1

    def test_condition_with_xss_string(self, client, db):
        """XSS strings in condition_grade are stored and returned as-is.

        The API does not sanitize output - frontend must handle escaping.
        This test verifies the string is preserved without corruption.

        Note: condition_grade is VARCHAR(20), so we use a shortened XSS
        string that still demonstrates the security principle.
        """
        from app.models import Book

        # Shortened to fit VARCHAR(20): "<b>xss</b>" is 10 chars
        xss_string = "<b>xss</b>"
        book = Book(
            title="XSS Test Book",
            condition_grade=xss_string,
            value_mid=100,
            inventory_type="PRIMARY",
        )
        db.add(book)
        db.commit()

        response = client.get("/api/v1/stats/by-condition")
        assert response.status_code == 200
        data = response.json()

        xss = next((c for c in data if c["condition"] == xss_string), None)
        assert xss is not None, f"XSS string should be stored and returned as-is: {xss_string}"
        assert xss["count"] == 1
        assert xss["value"] == 100

    def test_category_with_unicode(self, client):
        """Category names with Unicode characters render correctly."""
        unicode_category = "Litterature Francaise"
        client.post(
            "/api/v1/books",
            json={
                "title": "French Literature Book",
                "category": unicode_category,
                "value_mid": 300,
                "inventory_type": "PRIMARY",
            },
        )

        response = client.get("/api/v1/stats/by-category")
        assert response.status_code == 200
        data = response.json()

        french_cat = next((c for c in data if c["category"] == unicode_category), None)
        assert french_cat is not None, f"Unicode category not found in {data}"
        assert french_cat["count"] == 1
        assert french_cat["value"] == 300

    def test_category_with_sql_injection_string(self, client):
        """SQL injection strings in category are stored and returned as-is."""
        injection_string = "'; DROP TABLE books; --"
        client.post(
            "/api/v1/books",
            json={
                "title": "SQL Injection Category Book",
                "category": injection_string,
                "value_mid": 100,
                "inventory_type": "PRIMARY",
            },
        )

        response = client.get("/api/v1/stats/by-category")
        assert response.status_code == 200
        data = response.json()

        injection = next((c for c in data if c["category"] == injection_string), None)
        assert injection is not None, "Injection string should be returned as-is in category"
        assert injection["count"] == 1
        assert injection["value"] == 100

    def test_category_with_xss_string(self, client):
        """XSS strings in category are stored and returned as-is."""
        xss_string = "<script>alert('xss')</script>"
        client.post(
            "/api/v1/books",
            json={
                "title": "XSS Category Book",
                "category": xss_string,
                "value_mid": 100,
                "inventory_type": "PRIMARY",
            },
        )

        response = client.get("/api/v1/stats/by-category")
        assert response.status_code == 200
        data = response.json()

        xss = next((c for c in data if c["category"] == xss_string), None)
        assert xss is not None, "XSS string should be stored and returned as-is in category"
        assert xss["count"] == 1
        assert xss["value"] == 100

    def test_negative_value_mid_in_condition_stats(self, client, db):
        """Negative value_mid values are correctly summed in condition stats.

        While unusual, negative values could represent adjustments or credits.
        The sum calculation should handle them correctly.
        """
        from app.models import Book

        # Create books directly in DB to bypass potential API validation
        book1 = Book(
            title="Positive Value Book",
            condition_grade="GOOD",
            value_mid=100,
            inventory_type="PRIMARY",
        )
        book2 = Book(
            title="Negative Value Book",
            condition_grade="GOOD",
            value_mid=-50,
            inventory_type="PRIMARY",
        )
        db.add_all([book1, book2])
        db.commit()

        response = client.get("/api/v1/stats/by-condition")
        assert response.status_code == 200
        data = response.json()

        good = next((c for c in data if c["condition"] == "GOOD"), None)
        assert good is not None
        assert good["count"] == 2
        # Sum should be 100 + (-50) = 50
        assert good["value"] == 50, f"Expected 50, got {good['value']} (100 + -50)"

    def test_negative_value_mid_in_metrics_totals(self, client, db):
        """Negative value_mid values are correctly summed in metrics totals."""
        from app.models import Book

        book1 = Book(
            title="Positive Book",
            value_mid=200,
            purchase_price=150,
            inventory_type="PRIMARY",
        )
        book2 = Book(
            title="Negative Value Book",
            value_mid=-100,
            purchase_price=50,
            inventory_type="PRIMARY",
        )
        db.add_all([book1, book2])
        db.commit()

        response = client.get("/api/v1/stats/metrics")
        assert response.status_code == 200
        data = response.json()

        # Total current value should be 200 + (-100) = 100
        assert data["total_current_value"] == 100, (
            f"Expected 100, got {data['total_current_value']}"
        )
        # Purchase cost should be 150 + 50 = 200 (no negative there)
        assert data["total_purchase_cost"] == 200

    def test_very_long_condition_grade(self, client, db):
        """Very long condition grade strings are handled correctly.

        Tests at boundary of String(20) column limit.
        """
        from app.models import Book

        # condition_grade field is String(20) so test at boundary
        long_condition = "A" * 20  # Exactly at the limit
        book = Book(
            title="Long Condition Book",
            condition_grade=long_condition,
            value_mid=100,
            inventory_type="PRIMARY",
        )
        db.add(book)
        db.commit()

        response = client.get("/api/v1/stats/by-condition")
        assert response.status_code == 200
        data = response.json()

        long_cond = next((c for c in data if c["condition"] == long_condition), None)
        assert long_cond is not None, "Long condition grade should be stored"
        assert long_cond["count"] == 1

    def test_empty_string_condition_vs_null(self, client, db):
        """Empty string condition is distinct from null (Ungraded)."""
        from app.models import Book

        # Create book with empty string condition directly in DB
        book1 = Book(
            title="Empty Condition Book",
            condition_grade="",
            value_mid=100,
            inventory_type="PRIMARY",
        )
        book2 = Book(
            title="Null Condition Book",
            condition_grade=None,
            value_mid=100,
            inventory_type="PRIMARY",
        )
        db.add_all([book1, book2])
        db.commit()

        response = client.get("/api/v1/stats/by-condition")
        assert response.status_code == 200
        data = response.json()

        # Should have Ungraded entry for null condition
        ungraded = next((c for c in data if c["condition"] == "Ungraded"), None)
        assert ungraded is not None, "Null condition should show as Ungraded"
        assert ungraded["count"] >= 1

    def test_special_characters_in_dashboard_batch(self, client, db):
        """Dashboard batch endpoint handles special characters in multiple fields."""
        from app.models import Book

        # Create directly in DB to bypass API validation for condition_grade
        book = Book(
            title="Special <>&\"' Characters Book",
            condition_grade="FINE & RARE",
            category="Test <script>",
            value_mid=100,
            inventory_type="PRIMARY",
        )
        db.add(book)
        db.commit()

        response = client.get("/api/v1/stats/dashboard")
        assert response.status_code == 200
        data = response.json()

        # Verify the data is returned without errors
        assert "by_condition" in data
        assert "by_category" in data

        # Find our special character entries
        special_cond = next(
            (c for c in data["by_condition"] if c["condition"] == "FINE & RARE"), None
        )
        assert special_cond is not None, "Special character condition should be returned"

        special_cat = next(
            (c for c in data["by_category"] if c["category"] == "Test <script>"), None
        )
        assert special_cat is not None, "Special character category should be returned"

    def test_unicode_mixed_with_standard_in_aggregation(self, client, db):
        """Mixed Unicode and standard condition grades aggregate correctly."""
        from app.models import Book

        # Create via API with valid enum value
        client.post(
            "/api/v1/books",
            json={
                "title": "Standard Condition",
                "condition_grade": "GOOD",
                "value_mid": 100,
                "inventory_type": "PRIMARY",
            },
        )

        # Create directly in DB for legacy Unicode values
        book1 = Book(
            title="Unicode Condition 1",
            condition_grade="Bon Etat",
            value_mid=150,
            inventory_type="PRIMARY",
        )
        book2 = Book(
            title="Unicode Condition 2",
            condition_grade="Bon Etat",
            value_mid=200,
            inventory_type="PRIMARY",
        )
        db.add_all([book1, book2])
        db.commit()

        response = client.get("/api/v1/stats/by-condition")
        assert response.status_code == 200
        data = response.json()

        # Standard condition should be separate
        good = next((c for c in data if c["condition"] == "GOOD"), None)
        assert good is not None
        assert good["count"] == 1
        assert good["value"] == 100

        # Unicode conditions should be aggregated together
        bon_etat = next((c for c in data if c["condition"] == "Bon Etat"), None)
        assert bon_etat is not None
        assert bon_etat["count"] == 2
        assert bon_etat["value"] == 350  # 150 + 200

    def test_negative_value_in_week_delta_overview(self, client, db):
        """Negative values are correctly summed in week_delta calculations."""
        from datetime import date, timedelta

        from app.models import Book

        # Create books with purchase dates within the last week
        recent_date = date.today() - timedelta(days=3)

        book1 = Book(
            title="Positive Recent Book",
            value_mid=500,
            purchase_date=recent_date,
            inventory_type="PRIMARY",
            status="ON_HAND",
        )
        book2 = Book(
            title="Negative Recent Book",
            value_mid=-200,
            purchase_date=recent_date,
            inventory_type="PRIMARY",
            status="ON_HAND",
        )
        db.add_all([book1, book2])
        db.commit()

        response = client.get("/api/v1/stats/overview")
        assert response.status_code == 200
        data = response.json()

        # week_delta.value_mid should be 500 + (-200) = 300
        assert data["week_delta"]["value_mid"] == 300, (
            f"Expected 300, got {data['week_delta']['value_mid']}"
        )
        assert data["week_delta"]["count"] == 2


class TestDashboardCaching:
    """Tests for dashboard endpoint caching behavior."""

    def test_dashboard_returns_cached_response_on_hit(self, client):
        """Dashboard returns cached data when available."""
        from unittest.mock import MagicMock, patch

        cached_response = {
            "overview": {
                "primary": {
                    "count": 99,
                    "volumes": 99,
                    "value_low": 1000.0,
                    "value_mid": 1500.0,
                    "value_high": 2000.0,
                },
                "extended": {"count": 5},
                "flagged": {"count": 2},
                "total_items": 106,
                "authenticated_bindings": 10,
                "in_transit": 3,
                "week_delta": {
                    "count": 2,
                    "volumes": 2,
                    "value_mid": 100.0,
                    "authenticated_bindings": 1,
                },
            },
            "bindings": [],
            "by_era": [],
            "by_publisher": [],
            "by_author": [],
            "acquisitions_daily": [],
            "by_condition": [],
            "by_category": [],
        }

        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(cached_response)

        with patch("app.services.dashboard_stats.get_redis", return_value=mock_redis):
            response = client.get("/api/v1/stats/dashboard")

        assert response.status_code == 200
        data = response.json()
        # Should return cached count of 99
        assert data["overview"]["primary"]["count"] == 99

    def test_dashboard_caches_response_on_miss(self, client, db):
        """Dashboard caches response when cache is empty."""
        from unittest.mock import MagicMock, patch

        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # Cache miss

        with patch("app.services.dashboard_stats.get_redis", return_value=mock_redis):
            response = client.get("/api/v1/stats/dashboard")

        assert response.status_code == 200
        # Verify cache was set
        mock_redis.setex.assert_called_once()

    def test_dashboard_works_without_redis(self, client, db):
        """Dashboard works normally when Redis is unavailable."""
        from unittest.mock import patch

        with patch("app.services.dashboard_stats.get_redis", return_value=None):
            response = client.get("/api/v1/stats/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert "overview" in data
        assert "bindings" in data


class TestAcquisitionsDailyDefaults:
    """Tests for acquisition daily endpoint default values.

    Issue #1093: Value growth chart should default to 90 days (3 months).
    """

    def test_default_days_is_90(self):
        """Verify the default days parameter is 90 (3 months).

        The value growth chart should show 3 months by default, not 30 days.
        """
        import inspect

        from app.api.v1.stats import get_acquisitions_daily

        sig = inspect.signature(get_acquisitions_daily)
        days_param = sig.parameters["days"]

        # Extract the default from the Query object
        assert days_param.default.default == 90, (
            f"Expected default days=90 for 3-month chart, got {days_param.default.default}"
        )

    def test_dashboard_service_default_days_is_90(self):
        """Verify dashboard service function defaults to 90 days."""
        import inspect

        from app.services.dashboard_stats import get_dashboard_optimized

        sig = inspect.signature(get_dashboard_optimized)
        days_param = sig.parameters["days"]

        assert days_param.default == 90, (
            f"Expected default days=90 for dashboard service, got {days_param.default}"
        )
