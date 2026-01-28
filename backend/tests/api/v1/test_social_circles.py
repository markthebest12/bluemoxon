"""Tests for Social Circles API.

These tests ensure the endpoint returns valid data and would catch
import/attribute errors that cause 500s in production.
"""

from app.models import Author, Binder, Book, Publisher


class TestSocialCirclesEndpoint:
    """Tests for GET /api/v1/social-circles endpoint."""

    def test_endpoint_returns_200_with_empty_data(self, client, db):
        """Endpoint returns valid response even with no data."""
        response = client.get("/api/v1/social-circles")
        assert response.status_code == 200

        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert "meta" in data
        assert data["nodes"] == []
        assert data["edges"] == []

    def test_endpoint_returns_valid_structure(self, client, db):
        """Response structure matches schema."""
        # Create minimal test data
        author = Author(name="Test Author", birth_year=1850)
        db.add(author)
        db.flush()

        publisher = Publisher(name="Test Publisher")
        db.add(publisher)
        db.flush()

        book = Book(
            title="Test Book",
            author_id=author.id,
            publisher_id=publisher.id,
            status="ON_HAND",
        )
        db.add(book)
        db.commit()

        response = client.get("/api/v1/social-circles")
        assert response.status_code == 200

        data = response.json()

        # Verify meta structure
        assert "total_books" in data["meta"]
        assert "total_authors" in data["meta"]
        assert "total_publishers" in data["meta"]
        assert "total_binders" in data["meta"]
        assert "date_range" in data["meta"]
        assert "generated_at" in data["meta"]

        # Should have nodes for author and publisher
        assert len(data["nodes"]) >= 1

    def test_only_owned_books_included(self, client, db):
        """Only books with ON_HAND or IN_TRANSIT status are included."""
        author = Author(name="Test Author")
        db.add(author)
        db.flush()

        # Create books with different statuses
        owned_book = Book(title="Owned Book", author_id=author.id, status="ON_HAND")
        transit_book = Book(title="Transit Book", author_id=author.id, status="IN_TRANSIT")
        evaluating_book = Book(title="Evaluating Book", author_id=author.id, status="EVALUATING")
        removed_book = Book(title="Removed Book", author_id=author.id, status="REMOVED")
        db.add_all([owned_book, transit_book, evaluating_book, removed_book])
        db.commit()

        response = client.get("/api/v1/social-circles")
        assert response.status_code == 200

        data = response.json()
        # Should only count ON_HAND and IN_TRANSIT
        assert data["meta"]["total_books"] == 2

    def test_author_node_structure(self, client, db):
        """Author nodes have correct structure."""
        # Born 1850 = Victorian era (1837-1901)
        author = Author(
            name="Test Victorian Author", birth_year=1850, death_year=1920, tier="TIER_1"
        )
        db.add(author)
        db.flush()

        book = Book(title="Test Book", author_id=author.id, status="ON_HAND")
        db.add(book)
        db.commit()

        response = client.get("/api/v1/social-circles")
        assert response.status_code == 200

        data = response.json()
        author_nodes = [n for n in data["nodes"] if n["type"] == "author"]
        assert len(author_nodes) == 1

        node = author_nodes[0]
        assert node["id"] == f"author:{author.id}"
        assert node["entity_id"] == author.id
        assert node["name"] == "Test Victorian Author"
        assert node["birth_year"] == 1850
        assert node["death_year"] == 1920
        assert node["tier"] == "TIER_1"
        assert node["era"] == "victorian"
        assert node["book_count"] == 1

    def test_publisher_node_structure(self, client, db):
        """Publisher nodes have correct structure."""
        author = Author(name="Test Author")
        publisher = Publisher(name="Chapman and Hall", tier="TIER_1")
        db.add_all([author, publisher])
        db.flush()

        book = Book(
            title="Test Book", author_id=author.id, publisher_id=publisher.id, status="ON_HAND"
        )
        db.add(book)
        db.commit()

        response = client.get("/api/v1/social-circles")
        assert response.status_code == 200

        data = response.json()
        publisher_nodes = [n for n in data["nodes"] if n["type"] == "publisher"]
        assert len(publisher_nodes) == 1

        node = publisher_nodes[0]
        assert node["id"] == f"publisher:{publisher.id}"
        assert node["entity_id"] == publisher.id
        assert node["name"] == "Chapman and Hall"
        assert node["tier"] == "TIER_1"
        assert node["book_count"] == 1

    def test_author_publisher_edge_created(self, client, db):
        """Edge created between author and publisher when they share a book."""
        author = Author(name="Test Author")
        publisher = Publisher(name="Test Publisher")
        db.add_all([author, publisher])
        db.flush()

        book = Book(
            title="Test Book", author_id=author.id, publisher_id=publisher.id, status="ON_HAND"
        )
        db.add(book)
        db.commit()

        response = client.get("/api/v1/social-circles")
        assert response.status_code == 200

        data = response.json()
        edges = data["edges"]
        assert len(edges) >= 1

        # Find author-publisher edge
        author_pub_edges = [e for e in edges if e["type"] == "publisher"]
        assert len(author_pub_edges) == 1

        edge = author_pub_edges[0]
        assert edge["source"] == f"author:{author.id}"
        assert edge["target"] == f"publisher:{publisher.id}"
        assert edge["strength"] >= 1
        assert edge["strength"] <= 10


class TestSocialCirclesQueryParams:
    """Tests for query parameter handling."""

    def test_include_binders_true(self, client, db):
        """Binders included when include_binders=true."""
        author = Author(name="Test Author")
        binder = Binder(name="Test Binder")
        db.add_all([author, binder])
        db.flush()

        book = Book(title="Test Book", author_id=author.id, binder_id=binder.id, status="ON_HAND")
        db.add(book)
        db.commit()

        response = client.get("/api/v1/social-circles?include_binders=true")
        assert response.status_code == 200

        data = response.json()
        binder_nodes = [n for n in data["nodes"] if n["type"] == "binder"]
        assert len(binder_nodes) == 1

    def test_include_binders_false(self, client, db):
        """Binders excluded when include_binders=false."""
        author = Author(name="Test Author")
        binder = Binder(name="Test Binder")
        db.add_all([author, binder])
        db.flush()

        book = Book(title="Test Book", author_id=author.id, binder_id=binder.id, status="ON_HAND")
        db.add(book)
        db.commit()

        response = client.get("/api/v1/social-circles?include_binders=false")
        assert response.status_code == 200

        data = response.json()
        binder_nodes = [n for n in data["nodes"] if n["type"] == "binder"]
        assert len(binder_nodes) == 0

    def test_min_book_count_filter(self, client, db):
        """Entities with fewer books than min_book_count are excluded."""
        author1 = Author(name="Prolific Author")
        author2 = Author(name="One Book Author")
        db.add_all([author1, author2])
        db.flush()

        # Author 1 gets 3 books
        for i in range(3):
            book = Book(title=f"Book {i}", author_id=author1.id, status="ON_HAND")
            db.add(book)

        # Author 2 gets 1 book
        book = Book(title="Single Book", author_id=author2.id, status="ON_HAND")
        db.add(book)
        db.commit()

        response = client.get("/api/v1/social-circles?min_book_count=2")
        assert response.status_code == 200

        data = response.json()
        author_nodes = [n for n in data["nodes"] if n["type"] == "author"]
        assert len(author_nodes) == 1
        assert author_nodes[0]["name"] == "Prolific Author"

    def test_era_filter_single(self, client, db):
        """Filter by single era."""
        victorian = Author(name="Victorian Author", birth_year=1850)
        romantic = Author(name="Romantic Author", birth_year=1800)
        db.add_all([victorian, romantic])
        db.flush()

        for author in [victorian, romantic]:
            book = Book(title=f"Book by {author.name}", author_id=author.id, status="ON_HAND")
            db.add(book)
        db.commit()

        response = client.get("/api/v1/social-circles?era=victorian")
        assert response.status_code == 200

        data = response.json()
        author_nodes = [n for n in data["nodes"] if n["type"] == "author"]
        assert len(author_nodes) == 1
        assert author_nodes[0]["era"] == "victorian"

    def test_era_filter_multiple(self, client, db):
        """Filter by multiple eras."""
        victorian = Author(name="Victorian Author", birth_year=1850)
        romantic = Author(name="Romantic Author", birth_year=1800)
        edwardian = Author(name="Edwardian Author", birth_year=1905)
        db.add_all([victorian, romantic, edwardian])
        db.flush()

        for author in [victorian, romantic, edwardian]:
            book = Book(title=f"Book by {author.name}", author_id=author.id, status="ON_HAND")
            db.add(book)
        db.commit()

        response = client.get("/api/v1/social-circles?era=victorian&era=romantic")
        assert response.status_code == 200

        data = response.json()
        author_nodes = [n for n in data["nodes"] if n["type"] == "author"]
        assert len(author_nodes) == 2
        eras = {n["era"] for n in author_nodes}
        assert eras == {"victorian", "romantic"}


class TestSocialCirclesAuth:
    """Tests for authentication requirements."""

    def test_requires_authentication(self, unauthenticated_client, db):
        """Endpoint requires authentication."""
        response = unauthenticated_client.get("/api/v1/social-circles")
        assert response.status_code == 401

    def test_viewer_can_access(self, viewer_client, db):
        """Viewers can access the endpoint."""
        response = viewer_client.get("/api/v1/social-circles")
        assert response.status_code == 200


class TestSocialCirclesEdgeCases:
    """Tests for edge cases and complex scenarios."""

    def test_shared_publisher_edge(self, client, db):
        """Two authors with same publisher get shared_publisher edge."""
        author1 = Author(name="Author One")
        author2 = Author(name="Author Two")
        publisher = Publisher(name="Shared Publisher")
        db.add_all([author1, author2, publisher])
        db.flush()

        book1 = Book(
            title="Book One", author_id=author1.id, publisher_id=publisher.id, status="ON_HAND"
        )
        book2 = Book(
            title="Book Two", author_id=author2.id, publisher_id=publisher.id, status="ON_HAND"
        )
        db.add_all([book1, book2])
        db.commit()

        response = client.get("/api/v1/social-circles")
        assert response.status_code == 200

        data = response.json()
        shared_edges = [e for e in data["edges"] if e["type"] == "shared_publisher"]
        assert len(shared_edges) == 1

        edge = shared_edges[0]
        # Edge should connect the two authors
        assert "author:" in edge["source"]
        assert "author:" in edge["target"]
        assert "Shared Publisher" in edge["evidence"]

    def test_book_without_author_excluded(self, client, db):
        """Books without authors are handled gracefully."""
        publisher = Publisher(name="Test Publisher")
        db.add(publisher)
        db.flush()

        book = Book(
            title="Orphan Book", author_id=None, publisher_id=publisher.id, status="ON_HAND"
        )
        db.add(book)
        db.commit()

        response = client.get("/api/v1/social-circles")
        assert response.status_code == 200

        data = response.json()
        # Should not crash, publisher should not appear (no author connection)
        assert data["meta"]["total_books"] == 1

    def test_multiple_books_increase_edge_strength(self, client, db):
        """More shared books increase edge strength."""
        author = Author(name="Test Author")
        publisher = Publisher(name="Test Publisher")
        db.add_all([author, publisher])
        db.flush()

        # Create 5 books
        for i in range(5):
            book = Book(
                title=f"Book {i}", author_id=author.id, publisher_id=publisher.id, status="ON_HAND"
            )
            db.add(book)
        db.commit()

        response = client.get("/api/v1/social-circles")
        assert response.status_code == 200

        data = response.json()
        pub_edges = [e for e in data["edges"] if e["type"] == "publisher"]
        assert len(pub_edges) == 1

        # Strength should scale with books (max 10)
        assert pub_edges[0]["strength"] == 10  # 5 books * 2 = 10, capped at 10

    def test_era_assignment(self, client, db):
        """Authors assigned correct era based on birth year."""
        test_cases = [
            (1750, "pre_romantic"),
            (1800, "romantic"),
            (1850, "victorian"),
            (1905, "edwardian"),
            (1920, "post_1910"),
            (None, "unknown"),
        ]

        for birth_year, _expected_era in test_cases:
            author = Author(name=f"Author {birth_year}", birth_year=birth_year)
            db.add(author)
            db.flush()

            book = Book(title=f"Book by {birth_year}", author_id=author.id, status="ON_HAND")
            db.add(book)

        db.commit()

        response = client.get("/api/v1/social-circles")
        assert response.status_code == 200

        data = response.json()
        for node in data["nodes"]:
            if node["type"] == "author":
                birth = node.get("birth_year")
                expected = next(era for year, era in test_cases if year == birth)
                assert node["era"] == expected, (
                    f"Birth year {birth} should be {expected}, got {node['era']}"
                )


class TestTruncationBehavior:
    """Tests for the truncated flag in social circles response."""

    def test_truncated_false_when_under_limit(self, client, db):
        """truncated should be False when under MAX_BOOKS limit."""
        author = Author(name="Test Author")
        db.add(author)
        db.flush()

        book = Book(title="Test Book", author_id=author.id, status="ON_HAND")
        db.add(book)
        db.commit()

        response = client.get("/api/v1/social-circles")
        assert response.status_code == 200

        data = response.json()
        assert data["meta"]["truncated"] is False

    def test_truncated_flag_exists_in_meta(self, client, db):
        """Response meta should always include truncated flag."""
        response = client.get("/api/v1/social-circles")
        assert response.status_code == 200

        data = response.json()
        assert "truncated" in data["meta"]
        assert isinstance(data["meta"]["truncated"], bool)

    def test_truncated_false_with_empty_data(self, client, db):
        """truncated should be False when no books exist."""
        response = client.get("/api/v1/social-circles")
        assert response.status_code == 200

        data = response.json()
        assert data["meta"]["truncated"] is False
        assert data["meta"]["total_books"] == 0

    def test_truncated_false_with_moderate_data(self, client, db):
        """truncated should be False with moderate number of books."""
        author = Author(name="Prolific Author")
        db.add(author)
        db.flush()

        for i in range(100):
            book = Book(title=f"Book {i}", author_id=author.id, status="ON_HAND")
            db.add(book)
        db.commit()

        response = client.get("/api/v1/social-circles")
        assert response.status_code == 200

        data = response.json()
        assert data["meta"]["truncated"] is False
        assert data["meta"]["total_books"] == 100

    def test_total_books_reflects_actual_count(self, client, db):
        """total_books in meta should reflect the actual number of books processed."""
        author = Author(name="Test Author")
        db.add(author)
        db.flush()

        for i in range(50):
            book = Book(title=f"Book {i}", author_id=author.id, status="ON_HAND")
            db.add(book)
        db.commit()

        response = client.get("/api/v1/social-circles")
        assert response.status_code == 200

        data = response.json()
        assert data["meta"]["total_books"] == 50

    def test_non_owned_books_not_counted_in_total(self, client, db):
        """total_books should only count ON_HAND and IN_TRANSIT statuses."""
        author = Author(name="Test Author")
        db.add(author)
        db.flush()

        owned = Book(title="Owned", author_id=author.id, status="ON_HAND")
        transit = Book(title="Transit", author_id=author.id, status="IN_TRANSIT")
        evaluating = Book(title="Evaluating", author_id=author.id, status="EVALUATING")
        removed = Book(title="Removed", author_id=author.id, status="REMOVED")
        db.add_all([owned, transit, evaluating, removed])
        db.commit()

        response = client.get("/api/v1/social-circles")
        assert response.status_code == 200

        data = response.json()
        assert data["meta"]["total_books"] == 2
        assert data["meta"]["truncated"] is False
