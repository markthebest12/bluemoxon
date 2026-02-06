"""Tests for social circles graph builder AI edge merging and scope restriction (#1866, #1867)."""

from app.models import Author, Binder, Book, Publisher
from app.models.ai_connection import AIConnection
from app.services.social_circles import build_social_circles_graph, get_book_social_circles_summary


class TestAIEdgeMerge:
    """Tests for AI-discovered edges merged into social circles graph."""

    def test_ai_edges_appear_in_graph(self, db):
        """AI connections in the ai_connections table appear as edges in the graph."""
        author1 = Author(name="Elizabeth Barrett Browning", birth_year=1806, death_year=1861)
        author2 = Author(name="Robert Browning", birth_year=1812, death_year=1889)
        db.add_all([author1, author2])
        db.flush()

        # Both authors need at least one owned book to appear as nodes
        book1 = Book(title="Aurora Leigh", author_id=author1.id, status="ON_HAND", year_start=1857)
        book2 = Book(
            title="Ring and the Book", author_id=author2.id, status="ON_HAND", year_start=1868
        )
        db.add_all([book1, book2])
        db.flush()

        # Store AI connection in canonical table (lower node ID first)
        src_key = f"author:{author1.id}"
        tgt_key = f"author:{author2.id}"
        if src_key > tgt_key:
            s_type, s_id, t_type, t_id = "author", author2.id, "author", author1.id
        else:
            s_type, s_id, t_type, t_id = "author", author1.id, "author", author2.id

        db.add(
            AIConnection(
                source_type=s_type,
                source_id=s_id,
                target_type=t_type,
                target_id=t_id,
                relationship="family",
                sub_type="MARRIAGE",
                confidence=0.95,
                evidence="Married in 1846",
            )
        )
        db.commit()

        result = build_social_circles_graph(db)

        # Find AI edge
        ai_edges = [
            e
            for e in result.edges
            if e.type.value in ("family", "friendship", "influence", "collaboration", "scandal")
        ]
        assert len(ai_edges) >= 1
        family_edge = next(e for e in ai_edges if e.type.value == "family")
        assert "family" in family_edge.id
        assert family_edge.strength >= 2
        assert family_edge.evidence == "Married in 1846"

    def test_ai_edge_dedup_against_existing(self, db):
        """AI edges co-exist with book-derived edges for different relationship types."""
        author = Author(name="Test Author", birth_year=1820, death_year=1880)
        publisher = Publisher(name="Test Publisher")
        db.add_all([author, publisher])
        db.flush()

        # Book creates a publisher edge between them
        book = Book(
            title="Test Book",
            author_id=author.id,
            publisher_id=publisher.id,
            status="ON_HAND",
            year_start=1860,
        )
        db.add(book)
        db.flush()

        # AI connection for same pair but different type
        src_key = f"author:{author.id}"
        tgt_key = f"publisher:{publisher.id}"
        if src_key > tgt_key:
            s_type, s_id, t_type, t_id = "publisher", publisher.id, "author", author.id
        else:
            s_type, s_id, t_type, t_id = "author", author.id, "publisher", publisher.id

        db.add(
            AIConnection(
                source_type=s_type,
                source_id=s_id,
                target_type=t_type,
                target_id=t_id,
                relationship="friendship",
                confidence=0.8,
                evidence="Were friends",
            )
        )
        db.commit()

        result = build_social_circles_graph(db)

        # The book-derived publisher edge should exist
        pub_edges = [e for e in result.edges if e.type.value == "publisher"]
        assert len(pub_edges) >= 1

        # The AI friendship edge should ALSO exist since it's a different type
        friend_edges = [e for e in result.edges if e.type.value == "friendship"]
        assert len(friend_edges) >= 1

    def test_ai_edge_skipped_when_node_not_in_graph(self, db):
        """AI edges referencing entities not in the graph are silently skipped."""
        author = Author(name="Solo Author", birth_year=1830, death_year=1890)
        db.add(author)
        db.flush()

        book = Book(title="Solo Book", author_id=author.id, status="ON_HAND", year_start=1870)
        db.add(book)
        db.flush()

        # AI connection to non-existent author ID 9999
        db.add(
            AIConnection(
                source_type="author",
                source_id=author.id,
                target_type="author",
                target_id=9999,
                relationship="friendship",
                confidence=0.7,
                evidence="Were friends",
            )
        )
        db.commit()

        result = build_social_circles_graph(db)

        ai_edges = [
            e
            for e in result.edges
            if e.type.value in ("family", "friendship", "influence", "collaboration", "scandal")
        ]
        assert len(ai_edges) == 0

    def test_empty_ai_connections_handled(self, db):
        """No AI connections in table doesn't cause errors."""
        author = Author(name="Empty AI Author", birth_year=1840, death_year=1900)
        db.add(author)
        db.flush()

        book = Book(title="Empty AI Book", author_id=author.id, status="ON_HAND", year_start=1880)
        db.add(book)
        db.commit()

        result = build_social_circles_graph(db)
        # Should not crash, and no AI edges
        ai_edges = [
            e
            for e in result.edges
            if e.type.value in ("family", "friendship", "influence", "collaboration", "scandal")
        ]
        assert len(ai_edges) == 0


class TestScopeRestriction:
    """Tests for #1866: Social circles scope restricted to IN_TRANSIT and ON_HAND books."""

    def test_evaluating_books_excluded(self, db):
        """Books with EVALUATING status should not appear in social circles graph."""
        author = Author(name="Excluded Author", birth_year=1830, death_year=1890)
        db.add(author)
        db.flush()

        book = Book(
            title="Evaluating Book",
            author_id=author.id,
            status="EVALUATING",
            year_start=1860,
        )
        db.add(book)
        db.commit()

        result = build_social_circles_graph(db)
        author_nodes = [n for n in result.nodes if n.type.value == "author"]
        assert len(author_nodes) == 0

    def test_removed_books_excluded(self, db):
        """Books with REMOVED status should not appear in social circles graph."""
        author = Author(name="Removed Author", birth_year=1830, death_year=1890)
        db.add(author)
        db.flush()

        book = Book(
            title="Removed Book",
            author_id=author.id,
            status="REMOVED",
            year_start=1860,
        )
        db.add(book)
        db.commit()

        result = build_social_circles_graph(db)
        author_nodes = [n for n in result.nodes if n.type.value == "author"]
        assert len(author_nodes) == 0

    def test_in_transit_books_included(self, db):
        """Books with IN_TRANSIT status should appear in social circles graph."""
        author = Author(name="Transit Author", birth_year=1830, death_year=1890)
        db.add(author)
        db.flush()

        book = Book(
            title="Transit Book",
            author_id=author.id,
            status="IN_TRANSIT",
            year_start=1860,
        )
        db.add(book)
        db.commit()

        result = build_social_circles_graph(db)
        author_nodes = [n for n in result.nodes if n.type.value == "author"]
        assert len(author_nodes) == 1
        assert author_nodes[0].name == "Transit Author"

    def test_on_hand_books_included(self, db):
        """Books with ON_HAND status should appear in social circles graph."""
        author = Author(name="Owned Author", birth_year=1830, death_year=1890)
        db.add(author)
        db.flush()

        book = Book(
            title="Owned Book",
            author_id=author.id,
            status="ON_HAND",
            year_start=1860,
        )
        db.add(book)
        db.commit()

        result = build_social_circles_graph(db)
        author_nodes = [n for n in result.nodes if n.type.value == "author"]
        assert len(author_nodes) == 1
        assert author_nodes[0].name == "Owned Author"

    def test_mixed_status_only_qualifying_counted(self, db):
        """Author with both qualifying and non-qualifying books: only qualifying books counted."""
        author = Author(name="Mixed Author", birth_year=1830, death_year=1890)
        db.add(author)
        db.flush()

        owned = Book(title="Owned", author_id=author.id, status="ON_HAND", year_start=1860)
        removed = Book(title="Removed", author_id=author.id, status="REMOVED", year_start=1870)
        evaluating = Book(
            title="Evaluating", author_id=author.id, status="EVALUATING", year_start=1880
        )
        db.add_all([owned, removed, evaluating])
        db.commit()

        result = build_social_circles_graph(db)
        author_node = next(n for n in result.nodes if n.name == "Mixed Author")
        # Only the ON_HAND book should be counted
        assert author_node.book_count == 1

    def test_publisher_excluded_when_no_qualifying_books(self, db):
        """Publisher linked only to non-qualifying books should not appear."""
        author = Author(name="Test Author", birth_year=1830, death_year=1890)
        publisher = Publisher(name="Removed Publisher")
        db.add_all([author, publisher])
        db.flush()

        book = Book(
            title="Removed Book",
            author_id=author.id,
            publisher_id=publisher.id,
            status="REMOVED",
            year_start=1860,
        )
        db.add(book)
        db.commit()

        result = build_social_circles_graph(db)
        publisher_nodes = [n for n in result.nodes if n.type.value == "publisher"]
        assert len(publisher_nodes) == 0

    def test_binder_excluded_when_no_qualifying_books(self, db):
        """Binder linked only to non-qualifying books should not appear."""
        author = Author(name="Test Author", birth_year=1830, death_year=1890)
        binder = Binder(name="Removed Binder")
        db.add_all([author, binder])
        db.flush()

        book = Book(
            title="Removed Book",
            author_id=author.id,
            binder_id=binder.id,
            status="EVALUATING",
            year_start=1860,
        )
        db.add(book)
        db.commit()

        result = build_social_circles_graph(db)
        binder_nodes = [n for n in result.nodes if n.type.value == "binder"]
        assert len(binder_nodes) == 0


class TestBookSocialCirclesSummary:
    """Tests for #1867: Book social circles summary."""

    def test_summary_for_qualifying_book(self, db):
        """Summary returns connections for a book with ON_HAND status."""
        author = Author(name="Summary Author", birth_year=1830, death_year=1890)
        publisher = Publisher(name="Summary Publisher")
        db.add_all([author, publisher])
        db.flush()

        book = Book(
            title="Summary Book",
            author_id=author.id,
            publisher_id=publisher.id,
            status="ON_HAND",
            year_start=1860,
        )
        db.add(book)
        db.commit()

        summary = get_book_social_circles_summary(db, book.id)
        assert summary is not None
        assert summary["entity_count"] >= 1
        assert summary["connection_count"] >= 1
        assert len(summary["entity_node_ids"]) >= 1

    def test_summary_returns_none_for_non_qualifying(self, db):
        """Summary returns None for books not in qualifying status."""
        author = Author(name="Non-qual Author", birth_year=1830, death_year=1890)
        db.add(author)
        db.flush()

        book = Book(
            title="Removed Book",
            author_id=author.id,
            status="REMOVED",
            year_start=1860,
        )
        db.add(book)
        db.commit()

        summary = get_book_social_circles_summary(db, book.id)
        assert summary is None

    def test_summary_returns_none_for_missing_book(self, db):
        """Summary returns None for non-existent book."""
        summary = get_book_social_circles_summary(db, 99999)
        assert summary is None

    def test_summary_with_no_entities(self, db):
        """Summary handles book with no author/publisher/binder."""
        book = Book(
            title="Orphan Book",
            status="ON_HAND",
            year_start=1860,
        )
        db.add(book)
        db.commit()

        summary = get_book_social_circles_summary(db, book.id)
        assert summary is not None
        assert summary["entity_count"] == 0
        assert summary["connection_count"] == 0

    def test_summary_highlights_capped_at_3(self, db):
        """Summary highlights are capped at 3 entries."""
        author = Author(name="Connected Author", birth_year=1830, death_year=1890)
        publishers = [Publisher(name=f"Publisher {i}") for i in range(5)]
        db.add(author)
        db.add_all(publishers)
        db.flush()

        # Create books linking author to multiple publishers
        for p in publishers:
            book = Book(
                title=f"Book by {p.name}",
                author_id=author.id,
                publisher_id=p.id,
                status="ON_HAND",
                year_start=1860,
            )
            db.add(book)
        db.commit()

        # Use the first book for the summary
        first_book = db.query(Book).filter(Book.author_id == author.id).first()
        summary = get_book_social_circles_summary(db, first_book.id)
        assert summary is not None
        assert len(summary["highlights"]) <= 3

    def test_summary_in_transit_qualifies(self, db):
        """IN_TRANSIT books should qualify for summary."""
        author = Author(name="Transit Summary Author", birth_year=1830, death_year=1890)
        publisher = Publisher(name="Transit Summary Publisher")
        db.add_all([author, publisher])
        db.flush()

        book = Book(
            title="Transit Summary Book",
            author_id=author.id,
            publisher_id=publisher.id,
            status="IN_TRANSIT",
            year_start=1860,
        )
        db.add(book)
        db.commit()

        summary = get_book_social_circles_summary(db, book.id)
        assert summary is not None
        assert summary["connection_count"] >= 1
