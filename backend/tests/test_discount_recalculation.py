"""Tests for discount_pct recalculation."""

from decimal import Decimal

import pytest

from app.models.book import Book
from app.services.scoring import recalculate_discount_pct, recalculate_roi_pct


class TestRecalculateDiscountsEndpoint:
    """Tests for /health/recalculate-discounts maintenance endpoint."""

    def test_recalculates_all_stale_discounts(self, client, db):
        """Endpoint should recalculate discount_pct for all books with stale values."""
        # Create books with stale discount_pct values
        book1 = Book(
            title="Book with stale discount",
            purchase_price=Decimal("420.08"),
            value_mid=Decimal("950.00"),
            discount_pct=Decimal("-691.71"),  # Stale
            status="ON_HAND",
        )
        book2 = Book(
            title="Book with correct discount",
            purchase_price=Decimal("100.00"),
            value_mid=Decimal("200.00"),
            discount_pct=Decimal("50.00"),  # Already correct
            status="ON_HAND",
        )
        book3 = Book(
            title="Book without FMV",
            purchase_price=Decimal("100.00"),
            value_mid=None,
            discount_pct=None,
            status="ON_HAND",
        )
        db.add_all([book1, book2, book3])
        db.commit()

        response = client.post("/api/v1/health/recalculate-discounts")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["books_updated"] >= 1  # At least book1 should be updated

        # Verify book1 was recalculated
        db.refresh(book1)
        assert float(book1.discount_pct) == pytest.approx(55.78, rel=0.01)

        # Verify book2 stayed the same (already correct)
        db.refresh(book2)
        assert float(book2.discount_pct) == pytest.approx(50.00, rel=0.01)

        # Verify book3 still has None
        db.refresh(book3)
        assert book3.discount_pct is None

    def test_returns_count_of_updated_books(self, client, db):
        """Endpoint should return count of books that were updated."""
        book = Book(
            title="Stale book",
            purchase_price=Decimal("100.00"),
            value_mid=Decimal("500.00"),
            discount_pct=Decimal("10.00"),  # Wrong - should be 80%
            status="ON_HAND",
        )
        db.add(book)
        db.commit()

        response = client.post("/api/v1/health/recalculate-discounts")

        assert response.status_code == 200
        data = response.json()
        assert "books_updated" in data
        assert isinstance(data["books_updated"], int)


class TestDiscountRecalculationOnFMVUpdate:
    """Tests for automatic discount_pct recalculation when FMV is updated."""

    def test_patch_book_value_mid_recalculates_discount(self, client, db):
        """Updating value_mid via PATCH should recalculate discount_pct."""
        # Create book with initial discount
        book = Book(
            title="Test Book",
            purchase_price=Decimal("420.08"),
            value_mid=Decimal("53.00"),  # Low initial FMV
            discount_pct=Decimal("-692.60"),  # Calculated from low FMV
            status="ON_HAND",
        )
        db.add(book)
        db.commit()
        book_id = book.id

        # Update value_mid to corrected FMV
        response = client.put(
            f"/api/v1/books/{book_id}",
            json={"value_mid": "950.00"},
        )

        assert response.status_code == 200
        data = response.json()

        # discount_pct should be recalculated: (950 - 420.08) / 950 * 100 = 55.78%
        assert float(data["discount_pct"]) == pytest.approx(55.78, rel=0.01)

    def test_patch_book_value_mid_removes_discount_when_invalid(self, client, db):
        """Setting value_mid to 0 via PATCH should clear discount_pct."""
        book = Book(
            title="Test Book",
            purchase_price=Decimal("100.00"),
            value_mid=Decimal("200.00"),
            discount_pct=Decimal("50.00"),
            status="ON_HAND",
        )
        db.add(book)
        db.commit()
        book_id = book.id

        # Update value_mid to 0 (invalid for discount calculation)
        response = client.put(
            f"/api/v1/books/{book_id}",
            json={"value_mid": "0"},
        )

        assert response.status_code == 200
        data = response.json()

        # discount_pct should be None when value_mid is 0
        assert data["discount_pct"] is None


class TestRecalculateDiscountPct:
    """Tests for recalculate_discount_pct helper function."""

    def test_recalculates_discount_when_fmv_increased(self, db):
        """Discount should be recalculated when value_mid increases.

        This is the bug case: book had low FMV at acquisition ($53),
        FMV corrected to $950, but discount_pct stayed stale at -692%.
        """
        book = Book(
            title="Test Book",
            purchase_price=Decimal("420.08"),
            value_mid=Decimal("950.00"),  # Current (corrected) FMV
            discount_pct=Decimal("-691.71"),  # Stale value from old $53 FMV
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        recalculate_discount_pct(book)
        db.commit()

        # discount = (950 - 420.08) / 950 * 100 = 55.78%
        assert float(book.discount_pct) == pytest.approx(55.78, rel=0.01)

    def test_recalculates_discount_when_fmv_decreased(self, db):
        """Discount should be recalculated when value_mid decreases."""
        book = Book(
            title="Test Book",
            purchase_price=Decimal("100.00"),
            value_mid=Decimal("80.00"),  # FMV decreased below purchase price
            discount_pct=Decimal("50.00"),  # Stale positive discount
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        recalculate_discount_pct(book)
        db.commit()

        # discount = (80 - 100) / 80 * 100 = -25%
        assert float(book.discount_pct) == pytest.approx(-25.00, rel=0.01)

    def test_no_change_when_no_purchase_price(self, db):
        """Books without purchase_price should keep None discount_pct."""
        book = Book(
            title="Test Book",
            purchase_price=None,
            value_mid=Decimal("500.00"),
            discount_pct=None,
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        recalculate_discount_pct(book)
        db.commit()

        assert book.discount_pct is None

    def test_no_change_when_no_value_mid(self, db):
        """Books without value_mid should keep None discount_pct."""
        book = Book(
            title="Test Book",
            purchase_price=Decimal("100.00"),
            value_mid=None,
            discount_pct=None,
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        recalculate_discount_pct(book)
        db.commit()

        assert book.discount_pct is None

    def test_sets_none_when_values_become_invalid(self, db):
        """If value_mid becomes zero/None, discount_pct should become None."""
        book = Book(
            title="Test Book",
            purchase_price=Decimal("100.00"),
            value_mid=Decimal("0.00"),  # Invalid - division by zero case
            discount_pct=Decimal("50.00"),  # Stale value
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        recalculate_discount_pct(book)
        db.commit()

        assert book.discount_pct is None


class TestRecalculateRoiPct:
    """Tests for recalculate_roi_pct helper function."""

    def test_calculates_positive_roi(self, db):
        """ROI should be calculated correctly when FMV > acquisition cost."""
        book = Book(
            title="Test Book",
            acquisition_cost=Decimal("200.00"),
            value_mid=Decimal("500.00"),
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        recalculate_roi_pct(book)
        db.commit()

        # roi = (500 - 200) / 200 * 100 = 150%
        assert float(book.roi_pct) == pytest.approx(150.00, rel=0.01)

    def test_calculates_negative_roi(self, db):
        """ROI should be negative when FMV < acquisition cost (loss)."""
        book = Book(
            title="Test Book",
            acquisition_cost=Decimal("500.00"),
            value_mid=Decimal("400.00"),
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        recalculate_roi_pct(book)
        db.commit()

        # roi = (400 - 500) / 500 * 100 = -20%
        assert float(book.roi_pct) == pytest.approx(-20.00, rel=0.01)

    def test_no_change_when_no_acquisition_cost(self, db):
        """Books without acquisition_cost should keep None roi_pct."""
        book = Book(
            title="Test Book",
            acquisition_cost=None,
            value_mid=Decimal("500.00"),
            roi_pct=None,
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        recalculate_roi_pct(book)
        db.commit()

        assert book.roi_pct is None

    def test_no_change_when_no_value_mid(self, db):
        """Books without value_mid should keep None roi_pct."""
        book = Book(
            title="Test Book",
            acquisition_cost=Decimal("100.00"),
            value_mid=None,
            roi_pct=None,
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        recalculate_roi_pct(book)
        db.commit()

        assert book.roi_pct is None

    def test_sets_none_when_acquisition_cost_zero(self, db):
        """If acquisition_cost is zero, roi_pct should become None."""
        book = Book(
            title="Test Book",
            acquisition_cost=Decimal("0.00"),
            value_mid=Decimal("500.00"),
            roi_pct=Decimal("100.00"),  # Stale value
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        recalculate_roi_pct(book)
        db.commit()

        assert book.roi_pct is None

    def test_recalculates_when_fmv_updated(self, db):
        """ROI should be recalculated when value_mid changes."""
        book = Book(
            title="Test Book",
            acquisition_cost=Decimal("200.00"),
            value_mid=Decimal("300.00"),  # Changed from previous
            roi_pct=Decimal("100.00"),  # Stale ROI from previous FMV
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        recalculate_roi_pct(book)
        db.commit()

        # roi = (300 - 200) / 200 * 100 = 50%
        assert float(book.roi_pct) == pytest.approx(50.00, rel=0.01)
