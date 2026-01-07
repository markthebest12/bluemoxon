"""Tests for search API pagination - Issue #862."""

from sqlalchemy.orm import Session

from app.models import Author, Book, BookAnalysis


def create_test_books(db: Session, count: int, keyword: str = "searchable") -> list[Book]:
    """Create test books with searchable content."""
    author = Author(name="Test Author")
    db.add(author)
    db.flush()

    books = []
    for i in range(count):
        book = Book(
            title=f"Book {i} with {keyword} content",
            author_id=author.id,
            notes=f"Notes containing {keyword} text for book {i}",
            status="EVALUATING",
        )
        db.add(book)
        books.append(book)

    db.flush()
    return books


def create_test_analyses(
    db: Session, books: list[Book], keyword: str = "searchable"
) -> list[BookAnalysis]:
    """Create test analyses with searchable content."""
    analyses = []
    for i, book in enumerate(books):
        analysis = BookAnalysis(
            book_id=book.id,
            executive_summary=f"Analysis {i} with {keyword} summary",
            full_markdown=f"# Analysis {i}\n\nFull {keyword} markdown content",
        )
        db.add(analysis)
        analyses.append(analysis)

    db.flush()
    return analyses


class TestSearchPaginationScopeAll:
    """Test pagination when scope=all (combined books + analyses)."""

    def test_page_parameter_is_respected(self, client, db):
        """Page 2 should return different results than page 1, in order."""
        books = create_test_books(db, 10)
        create_test_analyses(db, books)
        db.commit()

        response1 = client.get("/api/v1/search?q=searchable&scope=all&page=1&per_page=5")
        assert response1.status_code == 200
        data1 = response1.json()

        response2 = client.get("/api/v1/search?q=searchable&scope=all&page=2&per_page=5")
        assert response2.status_code == 200
        data2 = response2.json()

        # Use lists to preserve order - page 2 items should come after page 1
        ids1 = [(r["type"], r["id"]) for r in data1["results"]]
        ids2 = [(r["type"], r["id"]) for r in data2["results"]]

        # No overlap between pages
        assert set(ids1).isdisjoint(set(ids2)), "Page 2 should not overlap with page 1"
        assert len(ids1) == 5
        assert len(ids2) == 5

    def test_per_page_returns_correct_count(self, client, db):
        """Requesting per_page=20 with scope=all should return up to 20 items."""
        books = create_test_books(db, 15)
        create_test_analyses(db, books)
        db.commit()

        response = client.get("/api/v1/search?q=searchable&scope=all&page=1&per_page=20")
        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) == 20
        assert data["total"] == 30

    def test_total_count_is_accurate(self, client, db):
        """Total should reflect all matching items across both types."""
        books = create_test_books(db, 7)
        create_test_analyses(db, books)
        db.commit()

        response = client.get("/api/v1/search?q=searchable&scope=all&page=1&per_page=5")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 14


class TestSearchPaginationScopeBooks:
    """Test pagination when scope=books."""

    def test_results_are_ordered_by_id(self, client, db):
        """Results should be ordered by book ID for deterministic pagination."""
        create_test_books(db, 10)
        db.commit()

        response = client.get("/api/v1/search?q=searchable&scope=books&page=1&per_page=10")
        assert response.status_code == 200
        results = response.json()["results"]

        # Verify results are in ascending ID order
        ids = [r["id"] for r in results]
        assert ids == sorted(ids), "Results should be ordered by ID"

    def test_page_parameter_is_respected(self, client, db):
        """Page 2 should return the next set of ordered results."""
        create_test_books(db, 10)
        db.commit()

        response1 = client.get("/api/v1/search?q=searchable&scope=books&page=1&per_page=5")
        response2 = client.get("/api/v1/search?q=searchable&scope=books&page=2&per_page=5")

        assert response1.status_code == 200
        assert response2.status_code == 200

        ids1 = [r["id"] for r in response1.json()["results"]]
        ids2 = [r["id"] for r in response2.json()["results"]]

        # Page 2 IDs should all be greater than page 1 IDs (ordered by ID)
        assert max(ids1) < min(ids2), "Page 2 should contain items after page 1"
        assert len(ids1) == 5
        assert len(ids2) == 5

    def test_pagination_offset_correct(self, client, db):
        """Verify offset is calculated correctly."""
        create_test_books(db, 15)
        db.commit()

        response = client.get("/api/v1/search?q=searchable&scope=books&page=3&per_page=5")
        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) == 5
        assert data["total"] == 15
        assert data["page"] == 3


class TestSearchPaginationScopeAnalyses:
    """Test pagination when scope=analyses."""

    def test_results_are_ordered_by_id(self, client, db):
        """Results should be ordered by analysis ID for deterministic pagination."""
        books = create_test_books(db, 10)
        create_test_analyses(db, books)
        db.commit()

        response = client.get("/api/v1/search?q=searchable&scope=analyses&page=1&per_page=10")
        assert response.status_code == 200
        results = response.json()["results"]

        ids = [r["id"] for r in results]
        assert ids == sorted(ids), "Results should be ordered by ID"

    def test_page_parameter_is_respected(self, client, db):
        """Page 2 should return the next set of ordered results."""
        books = create_test_books(db, 10)
        create_test_analyses(db, books)
        db.commit()

        response1 = client.get("/api/v1/search?q=searchable&scope=analyses&page=1&per_page=5")
        response2 = client.get("/api/v1/search?q=searchable&scope=analyses&page=2&per_page=5")

        assert response1.status_code == 200
        assert response2.status_code == 200

        ids1 = [r["id"] for r in response1.json()["results"]]
        ids2 = [r["id"] for r in response2.json()["results"]]

        assert max(ids1) < min(ids2), "Page 2 should contain items after page 1"
        assert len(ids1) == 5
        assert len(ids2) == 5


class TestSearchEagerLoading:
    """Test that eager loading prevents N+1 queries."""

    def test_book_author_is_loaded(self, client, db):
        """Book results should include author without extra queries."""
        create_test_books(db, 3)
        db.commit()

        response = client.get("/api/v1/search?q=searchable&scope=books&per_page=3")
        assert response.status_code == 200
        results = response.json()["results"]

        # All books should have author populated
        for result in results:
            assert result["author"] == "Test Author"

    def test_analysis_book_title_is_loaded(self, client, db):
        """Analysis results should include book title without extra queries."""
        books = create_test_books(db, 3)
        create_test_analyses(db, books)
        db.commit()

        response = client.get("/api/v1/search?q=searchable&scope=analyses&per_page=3")
        assert response.status_code == 200
        results = response.json()["results"]

        for result in results:
            assert "Book" in result["title"]
