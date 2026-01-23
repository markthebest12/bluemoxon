"""Tests for eager loading and N+1 query prevention.

Issue #1239: SQLAlchemy eager loading optimization.
"""

from sqlalchemy import event

from app.models import Author, Book, BookImage
from app.models.analysis import BookAnalysis
from app.models.eval_runbook import EvalRunbook


class QueryCounter:
    """Context manager to count SQL queries executed."""

    def __init__(self, connection):
        self.connection = connection
        self.count = 0

    def _callback(self, conn, cursor, statement, parameters, context, executemany):
        # Only count SELECT statements (not setup/transaction queries)
        if statement.strip().upper().startswith("SELECT"):
            self.count += 1

    def __enter__(self):
        event.listen(self.connection, "before_cursor_execute", self._callback)
        return self

    def __exit__(self, *args):
        event.remove(self.connection, "before_cursor_execute", self._callback)


class TestBooksListEagerLoading:
    """Tests for eager loading in books list endpoint."""

    def test_books_list_avoids_n_plus_1_queries(self, client, db):
        """Verify listing books doesn't cause N+1 queries for relationships.

        Without eager loading, listing N books causes:
        - 1 query for books
        - N queries for analysis (one per book)
        - N queries for eval_runbook (one per book)
        - N queries for images (one per book)
        = 1 + 3N queries total

        With proper eager loading, it should be a constant number of queries
        regardless of how many books are returned.
        """
        # Create 5 books with all relationships that the list endpoint accesses
        for i in range(5):
            book = Book(
                title=f"Victorian Book {i}",
                inventory_type="PRIMARY",
                status="ON_HAND",
            )
            db.add(book)
            db.flush()

            # Add analysis
            analysis = BookAnalysis(
                book_id=book.id,
                full_markdown=f"# Analysis for book {i}",
                executive_summary=f"Summary for book {i}",
                model_id="test-model",
            )
            db.add(analysis)

            # Add eval_runbook
            eval_runbook = EvalRunbook(
                book_id=book.id,
                total_score=80,
                score_breakdown={"test": 80},
                recommendation="ACQUIRE",
            )
            db.add(eval_runbook)

            # Add 2 images per book
            for j in range(2):
                image = BookImage(
                    book_id=book.id,
                    s3_key=f"images/book-{i}-{j}.jpg",
                    display_order=j,
                    is_primary=(j == 0),
                )
                db.add(image)

        db.commit()

        # Get the underlying connection for query counting
        connection = db.get_bind()

        with QueryCounter(connection) as counter:
            response = client.get("/api/v1/books?per_page=5")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 5

        # Verify relationships were loaded (checking response has the data)
        for item in data["items"]:
            assert item["has_analysis"] is True
            assert item["has_eval_runbook"] is True
            assert item["image_count"] == 2
            assert "primary_image_url" in item

        # With N+1, we'd have 1 + 3*5 = 16 SELECT queries
        # With eager loading, we should have at most 6 queries:
        # 1. COUNT for pagination
        # 2. Books with eager-loaded relationships (or separate SELECTs for each)
        # 3. Eval job status batch query
        # 4. Analysis job status batch query
        # Allow for selectinload which does separate queries per relationship
        # but still O(1) not O(n): books + analysis + eval_runbook + images = 4-6 queries
        # Plus the 2 job status queries = 6-8 total
        assert counter.count <= 10, (
            f"Expected at most 10 queries with eager loading, got {counter.count}. "
            "This suggests N+1 query problem - each book triggers separate queries "
            "for relationships instead of batch loading."
        )


class TestAuthorsListEagerLoading:
    """Tests for eager loading in authors list endpoint."""

    def test_authors_list_avoids_n_plus_1_queries(self, client, db):
        """Verify listing authors doesn't cause N+1 queries for book counts.

        Without optimization, listing N authors causes:
        - 1 query for authors
        - N queries for books (one per author to count books)
        = 1 + N queries total

        With proper optimization (subquery count or eager loading),
        it should be a constant number of queries.
        """
        # Create 5 authors with books
        for i in range(5):
            author = Author(name=f"Victorian Author {i}")
            db.add(author)
            db.flush()

            # Add 2 books per author
            for j in range(2):
                book = Book(
                    title=f"Book {j} by Author {i}",
                    author_id=author.id,
                    inventory_type="PRIMARY",
                    status="ON_HAND",
                )
                db.add(book)

        db.commit()

        connection = db.get_bind()

        with QueryCounter(connection) as counter:
            response = client.get("/api/v1/authors")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

        # Verify book counts are returned
        for item in data:
            assert item["book_count"] == 2

        # Without optimization: 1 + 5 = 6 queries
        # With subquery count or eager load: 1-2 queries
        assert counter.count <= 3, (
            f"Expected at most 3 queries for authors list, got {counter.count}. "
            "This suggests N+1 query problem for book counts."
        )


class TestBooksTopEagerLoading:
    """Tests for eager loading in top books endpoint."""

    def test_top_books_avoids_n_plus_1_queries(self, client, db):
        """Verify top books endpoint uses eager loading for images."""
        # Create 5 books with images
        # Top books requires value_mid > 0 for ranking
        for i in range(5):
            book = Book(
                title=f"Top Book {i}",
                inventory_type="PRIMARY",
                status="ON_HAND",
                value_mid=1000 - (i * 100),  # Descending values for top ranking
            )
            db.add(book)
            db.flush()

            # Add primary image
            image = BookImage(
                book_id=book.id,
                s3_key=f"images/top-{i}.jpg",
                display_order=0,
                is_primary=True,
            )
            db.add(image)

        db.commit()

        connection = db.get_bind()

        with QueryCounter(connection) as counter:
            response = client.get("/api/v1/books/top?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

        # Should be 2-3 queries max: books query + images (eager or selectin)
        assert counter.count <= 5, (
            f"Expected at most 5 queries for top books, got {counter.count}. "
            "This suggests N+1 query problem for images."
        )
