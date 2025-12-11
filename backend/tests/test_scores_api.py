"""Tests for score calculation API endpoints."""

from decimal import Decimal


class TestCalculateScoresEndpoint:
    """Tests for POST /books/{id}/scores/calculate endpoint."""

    def test_calculate_scores_returns_scores(self, client, db):
        """Should return calculated scores for a book."""
        from app.models.author import Author
        from app.models.book import Book
        from app.models.publisher import Publisher

        # Create test data
        author = Author(name="George Eliot", priority_score=0)
        publisher = Publisher(name="Blackwood", tier="TIER_1")
        db.add_all([author, publisher])
        db.commit()

        book = Book(
            title="Middlemarch",
            author_id=author.id,
            publisher_id=publisher.id,
            year_start=1871,
            volumes=1,
            condition_grade="Very Good",
            purchase_price=Decimal("300"),
            value_mid=Decimal("1000"),
            status="EVALUATING",
        )
        db.add(book)
        db.commit()

        response = client.post(f"/api/v1/books/{book.id}/scores/calculate")

        assert response.status_code == 200
        data = response.json()
        assert "investment_grade" in data
        assert "strategic_fit" in data
        assert "collection_impact" in data
        assert "overall_score" in data
        assert data["investment_grade"] == 100  # 70% discount

    def test_calculate_scores_persists_to_db(self, client, db):
        """Scores should be persisted to database."""
        from app.models.book import Book

        book = Book(
            title="Test Book",
            purchase_price=Decimal("500"),
            value_mid=Decimal("1000"),
            status="EVALUATING",
        )
        db.add(book)
        db.commit()
        book_id = book.id

        client.post(f"/api/v1/books/{book_id}/scores/calculate")

        db.expire_all()
        updated_book = db.get(Book, book_id)
        assert updated_book.investment_grade is not None
        assert updated_book.overall_score is not None
        assert updated_book.scores_calculated_at is not None

    def test_calculate_scores_404_for_missing_book(self, client):
        """Should return 404 for non-existent book."""
        response = client.post("/api/v1/books/99999/scores/calculate")
        assert response.status_code == 404


class TestAutoScoreOnCreate:
    """Tests for automatic score calculation on book creation."""

    def test_scores_calculated_on_create(self, client, db):
        """Creating a book should auto-calculate scores."""
        from app.models.author import Author
        from app.models.publisher import Publisher

        author = Author(name="Test Author")
        publisher = Publisher(name="Test Publisher", tier="TIER_1")
        db.add_all([author, publisher])
        db.commit()

        response = client.post(
            "/api/v1/books",
            json={
                "title": "Test Book",
                "author_id": author.id,
                "publisher_id": publisher.id,
                "year_start": 1867,
                "purchase_price": 300,
                "value_mid": 1000,
                "status": "EVALUATING",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["investment_grade"] is not None
        assert data["strategic_fit"] is not None
        assert data["overall_score"] is not None
