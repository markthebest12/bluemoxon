"""Tests for eager loading and N+1 query prevention.

Issue #1239: SQLAlchemy eager loading optimization.
"""

from sqlalchemy import event

from app.models import Author, Binder, Book, BookImage, Publisher
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

        # Expected queries for books list with eager loading:
        # 1. COUNT for pagination
        # 2. SELECT books
        # 3. SELECT analysis (selectinload)
        # 4. SELECT eval_runbook (selectinload)
        # 5. SELECT images (selectinload)
        # 6. Analysis job status batch query
        # 7. Eval job status batch query
        # Threshold: 7 queries + 3 buffer = 10
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

        # Expected queries for authors list:
        # 1. SELECT authors with book_count via correlated subquery
        # Threshold: 1 query + 2 buffer = 3
        assert counter.count <= 3, (
            f"Expected at most 3 queries for authors list, got {counter.count}. "
            "This suggests N+1 query problem for book counts."
        )


class TestPublishersListEagerLoading:
    """Tests for eager loading in publishers list endpoint."""

    def test_publishers_list_avoids_n_plus_1_queries(self, client, db):
        """Verify listing publishers doesn't cause N+1 queries for book counts."""
        # Create 5 publishers with books
        for i in range(5):
            publisher = Publisher(name=f"Victorian Publisher {i}")
            db.add(publisher)
            db.flush()

            # Add 2 books per publisher
            for j in range(2):
                book = Book(
                    title=f"Book {j} by Publisher {i}",
                    publisher_id=publisher.id,
                    inventory_type="PRIMARY",
                    status="ON_HAND",
                )
                db.add(book)

        db.commit()

        connection = db.get_bind()

        with QueryCounter(connection) as counter:
            response = client.get("/api/v1/publishers")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

        # Verify book counts are returned
        for item in data:
            assert item["book_count"] == 2

        # Expected queries for publishers list:
        # 1. SELECT publishers with book_count via correlated subquery
        # Threshold: 1 query + 2 buffer = 3
        assert counter.count <= 3, (
            f"Expected at most 3 queries for publishers list, got {counter.count}. "
            "This suggests N+1 query problem for book counts."
        )


class TestBindersListEagerLoading:
    """Tests for eager loading in binders list endpoint."""

    def test_binders_list_avoids_n_plus_1_queries(self, client, db):
        """Verify listing binders doesn't cause N+1 queries for book counts."""
        # Create 5 binders with books
        for i in range(5):
            binder = Binder(name=f"Victorian Binder {i}")
            db.add(binder)
            db.flush()

            # Add 2 books per binder
            for j in range(2):
                book = Book(
                    title=f"Book {j} by Binder {i}",
                    binder_id=binder.id,
                    inventory_type="PRIMARY",
                    status="ON_HAND",
                )
                db.add(book)

        db.commit()

        connection = db.get_bind()

        with QueryCounter(connection) as counter:
            response = client.get("/api/v1/binders")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

        # Verify book counts are returned
        for item in data:
            assert item["book_count"] == 2

        # Expected queries for binders list:
        # 1. SELECT binders with book_count via correlated subquery
        # Threshold: 1 query + 2 buffer = 3
        assert counter.count <= 3, (
            f"Expected at most 3 queries for binders list, got {counter.count}. "
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

        # Expected queries for top books endpoint:
        # 1. SELECT books (with ORDER BY value_mid, LIMIT)
        # 2. SELECT images (selectinload)
        # Threshold: 2 queries + 3 buffer = 5
        assert counter.count <= 5, (
            f"Expected at most 5 queries for top books, got {counter.count}. "
            "This suggests N+1 query problem for images."
        )


class TestBooksListScaling:
    """Tests to verify eager loading scales properly with dataset size."""

    def test_books_list_query_count_scales_with_page_size_not_data(self, client, db):
        """Verify that query count is O(1) not O(n) with larger datasets.

        With N+1 problem: 50 books would cause 1 + 3*50 = 151 queries
        With proper eager loading: should still be ~7-10 queries regardless of N
        """
        # Create 50 books with all relationships
        for i in range(50):
            book = Book(
                title=f"Scale Test Book {i}",
                inventory_type="PRIMARY",
                status="ON_HAND",
            )
            db.add(book)
            db.flush()

            # Add analysis
            analysis = BookAnalysis(
                book_id=book.id,
                full_markdown=f"# Analysis {i}",
                executive_summary=f"Summary {i}",
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

            # Add 1 image per book
            image = BookImage(
                book_id=book.id,
                s3_key=f"images/scale-{i}.jpg",
                display_order=0,
                is_primary=True,
            )
            db.add(image)

        db.commit()

        connection = db.get_bind()

        with QueryCounter(connection) as counter:
            response = client.get("/api/v1/books?per_page=50")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 50
        assert len(data["items"]) == 50

        # Expected queries at scale (50 books):
        # 1. COUNT for pagination
        # 2. SELECT books
        # 3. SELECT analysis (selectinload - still 1 query for all 50)
        # 4. SELECT eval_runbook (selectinload - still 1 query for all 50)
        # 5. SELECT images (selectinload - still 1 query for all 50)
        # 6. Analysis job status batch query
        # 7. Eval job status batch query
        # Threshold: 7 queries + 3 buffer = 10
        #
        # CRITICAL: With N+1 this would be 1 + 3*50 = 151 queries!
        assert counter.count <= 10, (
            f"Expected at most 10 queries at scale (50 books), got {counter.count}. "
            "With N+1 problem, this would be ~151 queries. "
            "Query count should be O(1) not O(n)."
        )
