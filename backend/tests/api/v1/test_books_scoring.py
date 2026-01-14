"""Tests for books scoring API endpoints.

Tests the /books/{id}/scores/calculate and /books/{id}/scores/breakdown endpoints
to ensure they correctly use the scoring service and exclude non-owned statuses
from the author_book_count calculation.

Fixes: https://github.com/markthebest12/bluemoxon/issues/1116
"""

import pytest

from app.enums import BookStatus
from app.models import Author, Book


class TestBooksScoringAPI:
    """Tests for book scoring API endpoints.

    These tests verify that the API endpoints in books.py correctly call
    the scoring service and respect status filtering for author_book_count.
    """

    @pytest.fixture
    def author(self, db):
        """Create a test author."""
        author = Author(name="George Borrow")
        db.add(author)
        db.commit()
        db.refresh(author)
        return author

    def test_scores_calculate_excludes_evaluating_from_author_count(self, client, db, author):
        """POST /books/{id}/scores/calculate should exclude EVALUATING from author count.

        When two books by the same author are both EVALUATING, neither should
        get the "second work by author" bonus because neither is owned.
        """
        # Create first book by author - EVALUATING
        book1 = Book(
            title="Lavengro",
            author_id=author.id,
            status=BookStatus.EVALUATING,
            value_mid=650,
            purchase_price=268,
        )
        db.add(book1)
        db.commit()
        db.refresh(book1)

        # Create second book by author - also EVALUATING
        book2 = Book(
            title="The Romany Rye",
            author_id=author.id,
            status=BookStatus.EVALUATING,
            value_mid=400,
            purchase_price=200,
        )
        db.add(book2)
        db.commit()
        db.refresh(book2)

        # Calculate scores via API
        response = client.post(f"/api/v1/books/{book2.id}/scores/calculate")
        assert response.status_code == 200

        data = response.json()
        # Both EVALUATING → author_book_count = 0 → "new author" bonus (+30)
        assert data["collection_impact"] == 30, (
            "API calculate should give 'new author' bonus (30) when other book is EVALUATING"
        )

    def test_scores_calculate_includes_on_hand_in_author_count(self, client, db, author):
        """POST /books/{id}/scores/calculate should include ON_HAND in author count."""
        # Create first book by author - ON_HAND (owned)
        book1 = Book(
            title="Lavengro",
            author_id=author.id,
            status=BookStatus.ON_HAND,
            value_mid=650,
            purchase_price=268,
        )
        db.add(book1)
        db.commit()
        db.refresh(book1)

        # Create second book by author - EVALUATING
        book2 = Book(
            title="The Romany Rye",
            author_id=author.id,
            status=BookStatus.EVALUATING,
            value_mid=400,
            purchase_price=200,
        )
        db.add(book2)
        db.commit()
        db.refresh(book2)

        # Calculate scores via API
        response = client.post(f"/api/v1/books/{book2.id}/scores/calculate")
        assert response.status_code == 200

        data = response.json()
        # ON_HAND counts → author_book_count = 1 → "second work" bonus (+15)
        assert data["collection_impact"] == 15, (
            "API calculate should give 'second work' bonus (15) when other book is ON_HAND"
        )

    def test_scores_breakdown_excludes_evaluating_from_author_count(self, client, db, author):
        """GET /books/{id}/scores/breakdown should exclude EVALUATING from author count.

        The breakdown endpoint should show "New author" factor, not "Second work"
        when other books by the author are in EVALUATING status.
        """
        # Create first book by author - EVALUATING
        book1 = Book(
            title="Lavengro",
            author_id=author.id,
            status=BookStatus.EVALUATING,
            value_mid=650,
            purchase_price=268,
        )
        db.add(book1)
        db.commit()
        db.refresh(book1)

        # Create second book by author - also EVALUATING
        book2 = Book(
            title="The Romany Rye",
            author_id=author.id,
            status=BookStatus.EVALUATING,
            value_mid=400,
            purchase_price=200,
        )
        db.add(book2)
        db.commit()
        db.refresh(book2)

        # Get score breakdown via API
        response = client.get(f"/api/v1/books/{book2.id}/scores/breakdown")
        assert response.status_code == 200

        data = response.json()
        # Check the breakdown shows "New author" factor with 30 points
        collection_breakdown = data["breakdown"]["collection_impact"]
        factors = {f["name"]: f for f in collection_breakdown["factors"]}

        assert "author_presence" in factors
        assert factors["author_presence"]["points"] == 30, (
            "Breakdown should show 30 points for author_presence (new author)"
        )
        assert "New author" in factors["author_presence"]["reason"], (
            "Breakdown reason should say 'New author' not 'Second work'"
        )

    def test_scores_breakdown_includes_on_hand_in_author_count(self, client, db, author):
        """GET /books/{id}/scores/breakdown should include ON_HAND in author count.

        The breakdown endpoint should show "Second work" factor when
        another book by the author is ON_HAND.
        """
        # Create first book by author - ON_HAND (owned)
        book1 = Book(
            title="Lavengro",
            author_id=author.id,
            status=BookStatus.ON_HAND,
            value_mid=650,
            purchase_price=268,
        )
        db.add(book1)
        db.commit()
        db.refresh(book1)

        # Create second book by author - EVALUATING
        book2 = Book(
            title="The Romany Rye",
            author_id=author.id,
            status=BookStatus.EVALUATING,
            value_mid=400,
            purchase_price=200,
        )
        db.add(book2)
        db.commit()
        db.refresh(book2)

        # Get score breakdown via API
        response = client.get(f"/api/v1/books/{book2.id}/scores/breakdown")
        assert response.status_code == 200

        data = response.json()
        # Check the breakdown shows "Second work" factor with 15 points
        collection_breakdown = data["breakdown"]["collection_impact"]
        factors = {f["name"]: f for f in collection_breakdown["factors"]}

        assert "author_presence" in factors
        assert factors["author_presence"]["points"] == 15, (
            "Breakdown should show 15 points for author_presence (second work)"
        )
        assert "Second work" in factors["author_presence"]["reason"], (
            "Breakdown reason should say 'Second work' when ON_HAND book exists"
        )

    def test_scores_calculate_excludes_removed_from_author_count(self, client, db, author):
        """POST /books/{id}/scores/calculate should exclude REMOVED from author count.

        REMOVED books are no longer in the collection and should not count
        toward the author_book_count.
        """
        # Create first book by author - REMOVED
        book1 = Book(
            title="Lavengro",
            author_id=author.id,
            status=BookStatus.REMOVED,
            value_mid=650,
            purchase_price=268,
        )
        db.add(book1)
        db.commit()
        db.refresh(book1)

        # Create second book by author - EVALUATING
        book2 = Book(
            title="The Romany Rye",
            author_id=author.id,
            status=BookStatus.EVALUATING,
            value_mid=400,
            purchase_price=200,
        )
        db.add(book2)
        db.commit()
        db.refresh(book2)

        # Calculate scores via API
        response = client.post(f"/api/v1/books/{book2.id}/scores/calculate")
        assert response.status_code == 200

        data = response.json()
        # REMOVED doesn't count → author_book_count = 0 → "new author" bonus (+30)
        assert data["collection_impact"] == 30, (
            "API calculate should give 'new author' bonus (30) when other book is REMOVED"
        )
