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


class TestDiscountPctOnBookCreation:
    """Tests for discount_pct calculation when creating books via POST.

    Bug #1078: create_book calls recalculate_roi_pct but NOT recalculate_discount_pct.
    """

    def test_create_book_calculates_discount_pct(self, client, db):
        """Creating book with purchase_price and value_mid should calculate discount_pct.

        This is the main bug: POST /books calculates roi_pct but not discount_pct.
        """
        response = client.post(
            "/api/v1/books",
            json={
                "title": "The Woman in White",
                "purchase_price": "448.00",
                "value_mid": "475.00",
                "status": "ON_HAND",
            },
        )

        assert response.status_code == 201
        data = response.json()

        # discount_pct should be calculated: (475 - 448) / 475 * 100 = 5.68%
        assert data["discount_pct"] is not None, "discount_pct should be calculated on create"
        assert float(data["discount_pct"]) == pytest.approx(5.68, rel=0.01)

    def test_create_book_calculates_both_discount_and_roi(self, client, db):
        """Creating book with all values should calculate both discount_pct and roi_pct."""
        response = client.post(
            "/api/v1/books",
            json={
                "title": "Val D'Arno",
                "purchase_price": "169.63",
                "acquisition_cost": "169.63",
                "value_mid": "260.00",
                "status": "ON_HAND",
            },
        )

        assert response.status_code == 201
        data = response.json()

        # discount_pct = (260 - 169.63) / 260 * 100 = 34.76%
        assert data["discount_pct"] is not None, "discount_pct should be calculated"
        assert float(data["discount_pct"]) == pytest.approx(34.76, rel=0.01)

        # roi_pct = (260 - 169.63) / 169.63 * 100 = 53.27%
        assert data["roi_pct"] is not None, "roi_pct should be calculated"
        assert float(data["roi_pct"]) == pytest.approx(53.27, rel=0.01)


class TestDiscountPctOnPurchasePriceUpdate:
    """Tests for discount_pct recalculation when purchase_price is updated.

    Bug #1078: update_book triggers recalculate_discount_pct only for value_* fields,
    not when purchase_price changes.
    """

    def test_update_purchase_price_recalculates_discount(self, client, db):
        """Updating purchase_price via PUT should recalculate discount_pct."""
        # Create book with initial values
        book = Book(
            title="Test Book",
            purchase_price=Decimal("100.00"),
            value_mid=Decimal("200.00"),
            discount_pct=Decimal("50.00"),  # Correct for 100/200
            status="ON_HAND",
        )
        db.add(book)
        db.commit()
        book_id = book.id

        # Update purchase_price - discount should recalculate
        response = client.put(
            f"/api/v1/books/{book_id}",
            json={"purchase_price": "150.00"},
        )

        assert response.status_code == 200
        data = response.json()

        # discount_pct should be recalculated: (200 - 150) / 200 * 100 = 25%
        assert float(data["discount_pct"]) == pytest.approx(25.00, rel=0.01)

    def test_update_purchase_price_alone_triggers_discount_recalc(self, client, db):
        """Updating ONLY purchase_price (not value_mid) should still recalculate discount."""
        book = Book(
            title="Test Book",
            purchase_price=Decimal("448.00"),
            value_mid=Decimal("475.00"),
            discount_pct=None,  # Bug: was never calculated
            status="ON_HAND",
        )
        db.add(book)
        db.commit()
        book_id = book.id

        # Update only purchase_price
        response = client.put(
            f"/api/v1/books/{book_id}",
            json={"purchase_price": "400.00"},
        )

        assert response.status_code == 200
        data = response.json()

        # discount_pct should be calculated: (475 - 400) / 475 * 100 = 15.79%
        assert data["discount_pct"] is not None, "discount_pct should be calculated when purchase_price changes"
        assert float(data["discount_pct"]) == pytest.approx(15.79, rel=0.01)


class TestClearingInputsClearsCalculatedFields:
    """Tests for clearing input values clears stale calculated percentages.

    P0 bug fix: When purchase_price or acquisition_cost is cleared, the corresponding
    calculated field (discount_pct or roi_pct) must also be cleared to prevent stale data.
    """

    def test_clearing_purchase_price_clears_discount_pct(self, client, db):
        """Setting purchase_price to null should clear discount_pct."""
        # Create book with calculated discount
        book = Book(
            title="Test Book",
            purchase_price=Decimal("100.00"),
            value_mid=Decimal("200.00"),
            discount_pct=Decimal("50.00"),  # Correct for 100/200
            status="ON_HAND",
        )
        db.add(book)
        db.commit()
        book_id = book.id

        # Clear purchase_price - discount should be cleared
        response = client.put(
            f"/api/v1/books/{book_id}",
            json={"purchase_price": None},
        )

        assert response.status_code == 200
        data = response.json()

        # discount_pct should be None since purchase_price is now null
        assert data["discount_pct"] is None, "discount_pct should be cleared when purchase_price is null"

    def test_clearing_value_mid_clears_discount_pct(self, client, db):
        """Setting value_mid to null should clear discount_pct."""
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

        # Clear value_mid - discount should be cleared
        response = client.put(
            f"/api/v1/books/{book_id}",
            json={"value_mid": None},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["discount_pct"] is None, "discount_pct should be cleared when value_mid is null"

    def test_clearing_acquisition_cost_clears_roi_pct(self, client, db):
        """Setting acquisition_cost to null should clear roi_pct."""
        book = Book(
            title="Test Book",
            acquisition_cost=Decimal("200.00"),
            value_mid=Decimal("500.00"),
            roi_pct=Decimal("150.00"),  # Correct for (500-200)/200
            status="ON_HAND",
        )
        db.add(book)
        db.commit()
        book_id = book.id

        # Clear acquisition_cost - roi should be cleared
        response = client.put(
            f"/api/v1/books/{book_id}",
            json={"acquisition_cost": None},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["roi_pct"] is None, "roi_pct should be cleared when acquisition_cost is null"

    def test_clearing_value_mid_clears_roi_pct(self, client, db):
        """Setting value_mid to null should clear roi_pct."""
        book = Book(
            title="Test Book",
            acquisition_cost=Decimal("200.00"),
            value_mid=Decimal("500.00"),
            roi_pct=Decimal("150.00"),
            status="ON_HAND",
        )
        db.add(book)
        db.commit()
        book_id = book.id

        # Clear value_mid - roi should be cleared
        response = client.put(
            f"/api/v1/books/{book_id}",
            json={"value_mid": None},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["roi_pct"] is None, "roi_pct should be cleared when value_mid is null"


class TestNegativeDiscountScenarios:
    """Tests for negative discount when purchase_price > value_mid (overpaid)."""

    def test_negative_discount_when_overpaid(self, client, db):
        """Negative discount should be calculated when purchase_price > value_mid."""
        response = client.post(
            "/api/v1/books",
            json={
                "title": "Overpaid Book",
                "purchase_price": "300.00",
                "value_mid": "200.00",  # Paid more than market value
                "status": "ON_HAND",
            },
        )

        assert response.status_code == 201
        data = response.json()

        # discount_pct = (200 - 300) / 200 * 100 = -50%
        assert data["discount_pct"] is not None
        assert float(data["discount_pct"]) == pytest.approx(-50.00, rel=0.01)

    def test_negative_discount_on_update(self, client, db):
        """Updating to overpaid state should calculate negative discount."""
        book = Book(
            title="Test Book",
            purchase_price=Decimal("100.00"),
            value_mid=Decimal("200.00"),
            discount_pct=Decimal("50.00"),  # Initially a good deal
            status="ON_HAND",
        )
        db.add(book)
        db.commit()
        book_id = book.id

        # Update value_mid to below purchase_price (market crashed)
        response = client.put(
            f"/api/v1/books/{book_id}",
            json={"value_mid": "80.00"},
        )

        assert response.status_code == 200
        data = response.json()

        # discount_pct = (80 - 100) / 80 * 100 = -25%
        assert float(data["discount_pct"]) == pytest.approx(-25.00, rel=0.01)


class TestCreateBookWithPartialData:
    """Tests for creating books with only some values present."""

    def test_create_book_with_only_purchase_price_no_value_mid(self, client, db):
        """Creating book with purchase_price but no value_mid should leave discount_pct null."""
        response = client.post(
            "/api/v1/books",
            json={
                "title": "Book Pending Valuation",
                "purchase_price": "100.00",
                # No value_mid - can't calculate discount yet
                "status": "ON_HAND",
            },
        )

        assert response.status_code == 201
        data = response.json()

        # discount_pct should be None since value_mid is missing
        assert data["discount_pct"] is None

    def test_adding_value_mid_later_calculates_discount(self, client, db):
        """Adding value_mid to book with existing purchase_price should calculate discount."""
        # Create book without value_mid
        book = Book(
            title="Book Pending Valuation",
            purchase_price=Decimal("100.00"),
            value_mid=None,
            discount_pct=None,
            status="ON_HAND",
        )
        db.add(book)
        db.commit()
        book_id = book.id

        # Add value_mid later
        response = client.put(
            f"/api/v1/books/{book_id}",
            json={"value_mid": "200.00"},
        )

        assert response.status_code == 200
        data = response.json()

        # discount_pct should now be calculated: (200 - 100) / 200 * 100 = 50%
        assert data["discount_pct"] is not None
        assert float(data["discount_pct"]) == pytest.approx(50.00, rel=0.01)
