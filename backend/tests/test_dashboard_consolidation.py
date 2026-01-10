"""Tests for consolidated dashboard queries.

These tests verify the new consolidated queries return identical results
to the original individual queries. After refactor is validated, parallel
comparison tests can be removed, keeping only property-based tests.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.api.v1.stats import get_by_category, get_by_condition, get_by_era, get_overview
from app.models import Author, Binder, Book, Publisher


@pytest.fixture
def db_with_diverse_books(db: Session):
    """Create test data covering all dimension combinations."""
    # Create publishers
    pub_tier1 = Publisher(name="Fine Press", tier="TIER_1")
    pub_tier2 = Publisher(name="Regular Press", tier="TIER_2")
    db.add_all([pub_tier1, pub_tier2])
    db.flush()

    # Create authors
    author1 = Author(name="Charles Dickens")
    author2 = Author(name="Jane Austen")
    db.add_all([author1, author2])
    db.flush()

    # Create binder
    binder = Binder(name="Riviere", full_name="Riviere & Son")
    db.add(binder)
    db.flush()

    # Create diverse books
    today = date.today()
    week_ago = today - timedelta(days=3)

    books = [
        # Victorian, FINE, Poetry, ON_HAND, authenticated
        Book(
            title="Victorian Poetry",
            year_start=1850,
            condition_grade="FINE",
            category="Poetry",
            status="ON_HAND",
            inventory_type="PRIMARY",
            value_low=Decimal("100"),
            value_mid=Decimal("150"),
            value_high=Decimal("200"),
            volumes=1,
            binding_authenticated=True,
            binder_id=binder.id,
            author_id=author1.id,
            publisher_id=pub_tier1.id,
            purchase_date=week_ago,
            purchase_price=Decimal("100"),
        ),
        # Victorian, GOOD, Fiction, ON_HAND
        Book(
            title="Victorian Fiction",
            year_start=1870,
            condition_grade="GOOD",
            category="Fiction",
            status="ON_HAND",
            inventory_type="PRIMARY",
            value_low=Decimal("50"),
            value_mid=Decimal("75"),
            value_high=Decimal("100"),
            volumes=2,
            author_id=author1.id,
            publisher_id=pub_tier2.id,
            purchase_date=today - timedelta(days=30),
            purchase_price=Decimal("50"),
        ),
        # Romantic, FAIR, History, ON_HAND
        Book(
            title="Romantic History",
            year_start=1820,
            condition_grade="FAIR",
            category="History",
            status="ON_HAND",
            inventory_type="PRIMARY",
            value_low=Decimal("30"),
            value_mid=Decimal("45"),
            value_high=Decimal("60"),
            volumes=1,
            author_id=author2.id,
            publisher_id=pub_tier2.id,
        ),
        # IN_TRANSIT book
        Book(
            title="In Transit Book",
            year_start=1880,
            condition_grade="FINE",
            category="Poetry",
            status="IN_TRANSIT",
            inventory_type="PRIMARY",
            value_mid=Decimal("200"),
            volumes=1,
            purchase_date=today,
            purchase_price=Decimal("150"),
        ),
        # EXTENDED inventory (should be excluded from most stats)
        Book(
            title="Extended Book",
            year_start=1860,
            condition_grade="GOOD",
            category="Fiction",
            status="ON_HAND",
            inventory_type="EXTENDED",
            value_mid=Decimal("25"),
        ),
    ]
    db.add_all(books)
    db.commit()

    return db


class TestPlaceholder:
    """Placeholder test to verify file loads."""

    def test_fixture_creates_books(self, db_with_diverse_books):
        """Verify fixture creates expected books."""
        db = db_with_diverse_books
        count = db.query(Book).filter(Book.inventory_type == "PRIMARY").count()
        assert count == 4  # 3 ON_HAND + 1 IN_TRANSIT


class TestDimensionStatsParallelComparison:
    """Verify consolidated dimension query matches individual queries."""

    def test_by_condition_matches(self, db_with_diverse_books):
        """Consolidated by_condition matches get_by_condition()."""
        db = db_with_diverse_books

        # Old way
        old_result = get_by_condition(db)

        # New way (will fail until implemented)
        from app.services.dashboard_stats import get_dimension_stats

        consolidated = get_dimension_stats(db)

        # Sort both for comparison
        old_sorted = sorted(old_result, key=lambda x: x["condition"] or "")
        new_sorted = sorted(consolidated["by_condition"], key=lambda x: x["condition"] or "")

        assert new_sorted == old_sorted

    def test_by_category_matches(self, db_with_diverse_books):
        """Consolidated by_category matches get_by_category()."""
        db = db_with_diverse_books

        old_result = get_by_category(db)

        from app.services.dashboard_stats import get_dimension_stats

        consolidated = get_dimension_stats(db)

        old_sorted = sorted(old_result, key=lambda x: x["category"])
        new_sorted = sorted(consolidated["by_category"], key=lambda x: x["category"])

        assert new_sorted == old_sorted

    def test_by_era_matches(self, db_with_diverse_books):
        """Consolidated by_era matches get_by_era()."""
        db = db_with_diverse_books

        old_result = get_by_era(db)

        from app.services.dashboard_stats import get_dimension_stats

        consolidated = get_dimension_stats(db)

        old_sorted = sorted(old_result, key=lambda x: x["era"])
        new_sorted = sorted(consolidated["by_era"], key=lambda x: x["era"])

        assert new_sorted == old_sorted


class TestOverviewStatsParallelComparison:
    """Verify consolidated overview query matches get_overview()."""

    def test_overview_matches(self, db_with_diverse_books):
        """Consolidated overview matches get_overview()."""
        db = db_with_diverse_books

        # Old way
        old_result = get_overview(db)

        # New way
        from app.services.dashboard_stats import get_overview_stats

        new_result = get_overview_stats(db)

        # Compare each section
        assert new_result["primary"] == old_result["primary"]
        assert new_result["extended"] == old_result["extended"]
        assert new_result["flagged"] == old_result["flagged"]
        assert new_result["total_items"] == old_result["total_items"]
        assert new_result["authenticated_bindings"] == old_result["authenticated_bindings"]
        assert new_result["in_transit"] == old_result["in_transit"]
        assert new_result["week_delta"] == old_result["week_delta"]
