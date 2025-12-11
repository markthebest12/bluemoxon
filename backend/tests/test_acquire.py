"""Tests for book acquisition endpoint."""

from decimal import Decimal

import pytest

from app.models.book import Book


@pytest.fixture
def evaluating_book(db):
    """Create a book in EVALUATING status for testing."""
    book = Book(
        title="Test Book for Acquisition",
        status="EVALUATING",
        inventory_type="PRIMARY",
        value_low=Decimal("400.00"),
        value_mid=Decimal("475.00"),
        value_high=Decimal("550.00"),
        volumes=1,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


class TestAcquireEndpoint:
    """Tests for PATCH /api/v1/books/{id}/acquire endpoint."""

    def test_acquire_changes_status_to_in_transit(self, client, evaluating_book):
        """Acquiring a book should change status from EVALUATING to IN_TRANSIT."""
        response = client.patch(
            f"/api/v1/books/{evaluating_book.id}/acquire",
            json={
                "purchase_price": 164.14,
                "purchase_date": "2025-12-10",
                "order_number": "19-13940-40744",
                "place_of_purchase": "eBay",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "IN_TRANSIT"
        assert float(data["purchase_price"]) == 164.14
        assert data["purchase_source"] == "eBay"

    def test_acquire_calculates_discount_percentage(self, client, evaluating_book):
        """Acquire should calculate discount_pct based on purchase_price vs value_mid."""
        response = client.patch(
            f"/api/v1/books/{evaluating_book.id}/acquire",
            json={
                "purchase_price": 164.14,
                "purchase_date": "2025-12-10",
                "order_number": "test-order",
                "place_of_purchase": "eBay",
            },
        )

        assert response.status_code == 200
        data = response.json()
        # discount = (475 - 164.14) / 475 * 100 = 65.44%
        assert float(data["discount_pct"]) == pytest.approx(65.44, rel=0.01)

    def test_acquire_creates_scoring_snapshot(self, client, evaluating_book):
        """Acquire should create a scoring_snapshot with acquisition-time data."""
        response = client.patch(
            f"/api/v1/books/{evaluating_book.id}/acquire",
            json={
                "purchase_price": 164.14,
                "purchase_date": "2025-12-10",
                "order_number": "test-order",
                "place_of_purchase": "eBay",
            },
        )

        assert response.status_code == 200
        data = response.json()
        snapshot = data["scoring_snapshot"]
        assert snapshot is not None
        assert "captured_at" in snapshot
        assert float(snapshot["purchase_price"]) == 164.14
        assert snapshot["fmv_at_purchase"]["mid"] == 475.0

    def test_acquire_rejects_non_evaluating_book(self, client, db):
        """Cannot acquire a book that is not in EVALUATING status."""
        book = Book(
            title="Already Acquired Book",
            status="ON_HAND",
            inventory_type="PRIMARY",
            volumes=1,
        )
        db.add(book)
        db.commit()

        response = client.patch(
            f"/api/v1/books/{book.id}/acquire",
            json={
                "purchase_price": 100.00,
                "purchase_date": "2025-12-10",
                "order_number": "test",
                "place_of_purchase": "eBay",
            },
        )

        assert response.status_code == 400
        assert "EVALUATING" in response.json()["detail"]

    def test_acquire_requires_editor_role(self, client, db, evaluating_book):
        """Acquire endpoint requires editor or admin role."""
        # Create a client WITHOUT the mocked auth to test unauthorized access
        from fastapi.testclient import TestClient

        from app.db import get_db
        from app.main import app

        # Create client with db override but NO auth override
        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        # Explicitly clear auth override to test unauthenticated access
        from app.auth import require_editor

        if require_editor in app.dependency_overrides:
            del app.dependency_overrides[require_editor]

        with TestClient(app) as test_client:
            response = test_client.patch(
                f"/api/v1/books/{evaluating_book.id}/acquire",
                json={
                    "purchase_price": 100.00,
                    "purchase_date": "2025-12-10",
                    "order_number": "test",
                    "place_of_purchase": "eBay",
                },
            )

            # Should fail without auth
            assert response.status_code in [401, 403]

        # Clean up
        app.dependency_overrides.clear()
