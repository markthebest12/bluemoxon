"""Tests for social circles graph builder AI edge merging."""

from app.models import Author, Book, Publisher
from app.models.entity_profile import EntityProfile
from app.services.social_circles import build_social_circles_graph


class TestAIEdgeMerge:
    """Tests for AI-discovered edges merged into social circles graph."""

    def test_ai_edges_appear_in_graph(self, db):
        """AI connections stored in entity_profiles appear as edges in the graph."""
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

        # Store AI connection on one of the profiles
        profile = EntityProfile(
            entity_type="author",
            entity_id=author1.id,
            ai_connections=[
                {
                    "source_type": "author",
                    "source_id": author1.id,
                    "target_type": "author",
                    "target_id": author2.id,
                    "relationship": "family",
                    "sub_type": "MARRIAGE",
                    "confidence": 0.95,
                    "evidence": "Married in 1846",
                }
            ],
        )
        db.add(profile)
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
        """AI edges are skipped if the same node pair already has a book-derived edge."""
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

        # AI connection for same pair
        profile = EntityProfile(
            entity_type="author",
            entity_id=author.id,
            ai_connections=[
                {
                    "source_type": "author",
                    "source_id": author.id,
                    "target_type": "publisher",
                    "target_id": publisher.id,
                    "relationship": "friendship",
                    "confidence": 0.8,
                    "evidence": "Were friends",
                }
            ],
        )
        db.add(profile)
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
        profile = EntityProfile(
            entity_type="author",
            entity_id=author.id,
            ai_connections=[
                {
                    "source_type": "author",
                    "source_id": author.id,
                    "target_type": "author",
                    "target_id": 9999,
                    "relationship": "friendship",
                    "confidence": 0.7,
                    "evidence": "Were friends",
                }
            ],
        )
        db.add(profile)
        db.commit()

        result = build_social_circles_graph(db)

        ai_edges = [
            e
            for e in result.edges
            if e.type.value in ("family", "friendship", "influence", "collaboration", "scandal")
        ]
        assert len(ai_edges) == 0

    def test_empty_ai_connections_handled(self, db):
        """Profiles with empty ai_connections don't cause errors."""
        author = Author(name="Empty AI Author", birth_year=1840, death_year=1900)
        db.add(author)
        db.flush()

        book = Book(title="Empty AI Book", author_id=author.id, status="ON_HAND", year_start=1880)
        db.add(book)
        db.flush()

        profile = EntityProfile(
            entity_type="author",
            entity_id=author.id,
            ai_connections=[],
        )
        db.add(profile)
        db.commit()

        result = build_social_circles_graph(db)
        # Should not crash, and no AI edges
        ai_edges = [
            e
            for e in result.edges
            if e.type.value in ("family", "friendship", "influence", "collaboration", "scandal")
        ]
        assert len(ai_edges) == 0
