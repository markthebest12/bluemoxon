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


class TestBatchCalculateScores:
    """Tests for POST /books/scores/calculate-all endpoint."""

    def test_batch_calculate_updates_all_books(self, client, db):
        """Should update scores for all books."""
        from app.models.book import Book

        # Create test books
        for i in range(3):
            book = Book(
                title=f"Test Book {i}",
                purchase_price=Decimal("500"),
                value_mid=Decimal("1000"),
            )
            db.add(book)
        db.commit()

        response = client.post("/api/v1/books/scores/calculate-all")

        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 3
        assert len(data["errors"]) == 0


class TestScoreBreakdownEndpoint:
    """Tests for GET /books/{id}/scores/breakdown endpoint."""

    def test_breakdown_returns_detailed_factors(self, client, db):
        """Should return score breakdown with factor explanations."""
        from app.models.author import Author
        from app.models.book import Book
        from app.models.publisher import Publisher

        author = Author(name="George Eliot", priority_score=50)
        publisher = Publisher(name="Smith Elder", tier="TIER_1")
        db.add_all([author, publisher])
        db.commit()

        book = Book(
            title="Felix Holt, the Radical",
            author_id=author.id,
            publisher_id=publisher.id,
            year_start=1866,
            volumes=1,
            condition_grade="Very Good",
            purchase_price=Decimal("200"),
            value_mid=Decimal("600"),
            status="EVALUATING",
        )
        db.add(book)
        db.commit()

        response = client.get(f"/api/v1/books/{book.id}/scores/breakdown")

        assert response.status_code == 200
        data = response.json()

        # Check top-level scores
        assert "investment_grade" in data
        assert "strategic_fit" in data
        assert "collection_impact" in data
        assert "overall_score" in data

        # Check breakdown structure
        assert "breakdown" in data
        assert "investment_grade" in data["breakdown"]
        assert "strategic_fit" in data["breakdown"]
        assert "collection_impact" in data["breakdown"]

        # Check factors contain entity names
        sf_factors = data["breakdown"]["strategic_fit"]["factors"]
        factor_names = [f["name"] for f in sf_factors]
        assert "publisher_tier" in factor_names
        assert "era" in factor_names
        assert "author_priority" in factor_names

        # Check publisher name appears in reason
        pub_factor = next(f for f in sf_factors if f["name"] == "publisher_tier")
        assert "Smith Elder" in pub_factor["reason"]

        # Check author name appears
        author_factor = next(f for f in sf_factors if f["name"] == "author_priority")
        assert "George Eliot" in author_factor["reason"]

    def test_breakdown_404_for_missing_book(self, client):
        """Should return 404 for non-existent book."""
        response = client.get("/api/v1/books/99999/scores/breakdown")
        assert response.status_code == 404

    def test_breakdown_handles_missing_data(self, client, db):
        """Should handle books with minimal data gracefully."""
        from app.models.book import Book

        book = Book(
            title="Unknown Book",
            status="EVALUATING",
        )
        db.add(book)
        db.commit()

        response = client.get(f"/api/v1/books/{book.id}/scores/breakdown")

        assert response.status_code == 200
        data = response.json()
        assert data["investment_grade"] == 0  # Missing price data
        assert "breakdown" in data
        # Should have missing_data factor
        ig_factors = data["breakdown"]["investment_grade"]["factors"]
        assert any("missing" in f["reason"].lower() for f in ig_factors)
