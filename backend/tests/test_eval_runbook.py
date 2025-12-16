"""Tests for eval runbook API endpoints."""

from decimal import Decimal

import pytest

from app.models import Book, EvalRunbook


class TestGetEvalRunbook:
    """Tests for GET /books/{id}/eval-runbook."""

    def test_returns_runbook_when_exists(self, client, db):
        """Test successful retrieval of eval runbook."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        runbook = EvalRunbook(
            book_id=book.id,
            total_score=65,
            score_breakdown={"Tier 1 Publisher": {"points": 0, "notes": "Not Tier 1"}},
            recommendation="PASS",
            original_asking_price=Decimal("275.00"),
            current_asking_price=Decimal("275.00"),
            fmv_low=Decimal("180.00"),
            fmv_high=Decimal("220.00"),
        )
        db.add(runbook)
        db.commit()

        response = client.get(f"/api/v1/books/{book.id}/eval-runbook")

        assert response.status_code == 200
        data = response.json()
        assert data["total_score"] == 65
        assert data["recommendation"] == "PASS"

    def test_returns_404_when_not_found(self, client, db):
        """Test 404 when runbook doesn't exist."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        response = client.get(f"/api/v1/books/{book.id}/eval-runbook")

        assert response.status_code == 404

    def test_returns_404_for_nonexistent_book(self, client):
        """Test 404 when book doesn't exist."""
        response = client.get("/api/v1/books/99999/eval-runbook")

        assert response.status_code == 404


class TestUpdatePrice:
    """Tests for PATCH /books/{id}/eval-runbook/price."""

    def test_updates_price_and_recalculates_score(self, client, db):
        """Test price update triggers score recalculation."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        runbook = EvalRunbook(
            book_id=book.id,
            total_score=60,
            score_breakdown={
                "Tier 1 Publisher": {"points": 0, "notes": "Not Tier 1"},
                "Victorian Era": {"points": 30, "notes": "1854"},
                "Complete Set": {"points": 20, "notes": "Single volume"},
                "Condition": {"points": 10, "notes": "Good+"},
                "Premium Binding": {"points": 0, "notes": "No binder"},
                "Price vs FMV": {"points": 0, "notes": "Above market"},
            },
            recommendation="PASS",
            original_asking_price=Decimal("275.00"),
            current_asking_price=Decimal("275.00"),
            fmv_low=Decimal("180.00"),
            fmv_high=Decimal("220.00"),
        )
        db.add(runbook)
        db.commit()

        response = client.patch(
            f"/api/v1/books/{book.id}/eval-runbook/price",
            json={"new_price": 160.00, "discount_code": "SAVE20", "notes": "Negotiated"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["previous_price"] == "275.00"
        assert data["new_price"] == "160.0"
        assert data["score_before"] == 60
        assert data["score_after"] > 60  # Should increase with better price
        assert data["runbook"]["discount_code"] == "SAVE20"

    def test_creates_price_history_record(self, client, db):
        """Test price update creates history record."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        runbook = EvalRunbook(
            book_id=book.id,
            total_score=60,
            score_breakdown={"Price vs FMV": {"points": 0, "notes": "Above market"}},
            recommendation="PASS",
            current_asking_price=Decimal("275.00"),
            fmv_low=Decimal("180.00"),
            fmv_high=Decimal("220.00"),
        )
        db.add(runbook)
        db.commit()

        client.patch(
            f"/api/v1/books/{book.id}/eval-runbook/price",
            json={"new_price": 200.00},
        )

        # Check history
        response = client.get(f"/api/v1/books/{book.id}/eval-runbook/history")
        assert response.status_code == 200
        history = response.json()
        assert len(history) == 1
        assert history[0]["previous_price"] == "275.00"
        assert history[0]["new_price"] == "200.00"

    def test_returns_404_when_runbook_not_found(self, client, db):
        """Test 404 when runbook doesn't exist for price update."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        response = client.patch(
            f"/api/v1/books/{book.id}/eval-runbook/price",
            json={"new_price": 200.00},
        )

        assert response.status_code == 404

    def test_returns_404_for_nonexistent_book(self, client):
        """Test 404 when book doesn't exist for price update."""
        response = client.patch(
            "/api/v1/books/99999/eval-runbook/price",
            json={"new_price": 200.00},
        )

        assert response.status_code == 404


class TestGetPriceHistory:
    """Tests for GET /books/{id}/eval-runbook/history."""

    def test_returns_empty_history_when_no_changes(self, client, db):
        """Test returns empty list when no price changes."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        runbook = EvalRunbook(
            book_id=book.id,
            total_score=65,
            score_breakdown={},
            recommendation="PASS",
            current_asking_price=Decimal("275.00"),
        )
        db.add(runbook)
        db.commit()

        response = client.get(f"/api/v1/books/{book.id}/eval-runbook/history")

        assert response.status_code == 200
        history = response.json()
        assert history == []

    def test_returns_404_when_runbook_not_found(self, client, db):
        """Test 404 when runbook doesn't exist."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        response = client.get(f"/api/v1/books/{book.id}/eval-runbook/history")

        assert response.status_code == 404

    def test_returns_404_for_nonexistent_book(self, client):
        """Test 404 when book doesn't exist."""
        response = client.get("/api/v1/books/99999/eval-runbook/history")

        assert response.status_code == 404

    def test_returns_history_in_chronological_order(self, client, db):
        """Test history is returned in descending order (newest first)."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        runbook = EvalRunbook(
            book_id=book.id,
            total_score=60,
            score_breakdown={"Price vs FMV": {"points": 0, "notes": "Above market"}},
            recommendation="PASS",
            current_asking_price=Decimal("300.00"),
            fmv_low=Decimal("180.00"),
            fmv_high=Decimal("220.00"),
        )
        db.add(runbook)
        db.commit()

        # Make first price change
        client.patch(
            f"/api/v1/books/{book.id}/eval-runbook/price",
            json={"new_price": 250.00},
        )

        # Make second price change
        client.patch(
            f"/api/v1/books/{book.id}/eval-runbook/price",
            json={"new_price": 200.00},
        )

        # Check history
        response = client.get(f"/api/v1/books/{book.id}/eval-runbook/history")
        assert response.status_code == 200
        history = response.json()
        assert len(history) == 2
        # Newest first
        assert history[0]["new_price"] == "200.00"
        assert history[1]["new_price"] == "250.00"
