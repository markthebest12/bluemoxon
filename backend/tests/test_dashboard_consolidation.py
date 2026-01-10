"""Tests for consolidated dashboard queries.

These tests verify the new consolidated queries return identical results
to the original individual queries. After refactor is validated, parallel
comparison tests can be removed, keeping only property-based tests.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

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
