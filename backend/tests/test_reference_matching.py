import pytest

from app.services.listing import (
    jaccard_similarity,
    match_author,
    match_binder,
    match_publisher,
    match_reference,
    normalize_name,
)


class TestNameNormalization:
    def test_lowercase(self):
        assert normalize_name("John Ruskin") == "john ruskin"

    def test_remove_and_son(self):
        assert normalize_name("Rivière & Son") == "riviere"
        assert normalize_name("Zaehnsdorf & Co.") == "zaehnsdorf"

    def test_remove_punctuation(self):
        assert normalize_name("Smith, Elder & Co.") == "smith elder"

    def test_preserve_initials(self):
        assert normalize_name("J. Ruskin") == "j ruskin"

    def test_remove_ltd(self):
        assert normalize_name("Macmillan Ltd.") == "macmillan"
        assert normalize_name("Random House Inc.") == "random house"


class TestJaccardSimilarity:
    def test_identical(self):
        assert jaccard_similarity("john ruskin", "john ruskin") == 1.0

    def test_partial_overlap(self):
        # "j ruskin" tokens: {j, ruskin}, "john ruskin" tokens: {john, ruskin}
        # intersection: {ruskin}, union: {j, john, ruskin}
        sim = jaccard_similarity("j ruskin", "john ruskin")
        assert 0.3 <= sim <= 0.4  # 1/3

    def test_no_overlap(self):
        assert jaccard_similarity("foo bar", "baz qux") == 0.0

    def test_empty_string(self):
        assert jaccard_similarity("", "test") == 0.0


class TestMatchReference:
    def test_exact_match(self):
        records = [(1, "John Ruskin"), (2, "Charles Dickens")]
        result = match_reference("John Ruskin", records, threshold=0.9)
        assert result == {"id": 1, "name": "John Ruskin", "similarity": 1.0}

    def test_no_match_below_threshold(self):
        records = [(1, "John Ruskin"), (2, "Charles Dickens")]
        result = match_reference("William Shakespeare", records, threshold=0.9)
        assert result is None

    def test_partial_match_above_threshold(self):
        records = [(1, "Rivière & Son")]
        # "riviere" normalized matches well with "riviere" from "Rivière & Son"
        result = match_reference("Riviere", records, threshold=0.5)
        assert result is not None
        assert result["id"] == 1


class TestDatabaseMatching:
    """Tests that require database fixtures."""

    @pytest.fixture
    def sample_authors(self, db):
        """Create sample authors for testing."""
        from app.models import Author

        a1 = Author(name="John Ruskin")
        a2 = Author(name="Charles Dickens")
        db.add_all([a1, a2])
        db.commit()
        db.refresh(a1)
        db.refresh(a2)
        return [a1, a2]

    @pytest.fixture
    def sample_publishers(self, db):
        """Create sample publishers for testing."""
        from app.models import Publisher

        p1 = Publisher(name="Smith, Elder & Co.")
        p2 = Publisher(name="Chapman & Hall")
        db.add_all([p1, p2])
        db.commit()
        db.refresh(p1)
        db.refresh(p2)
        return [p1, p2]

    @pytest.fixture
    def sample_binders(self, db):
        """Create sample binders for testing."""
        from app.models import Binder

        b1 = Binder(name="Rivière & Son")
        b2 = Binder(name="Zaehnsdorf")
        db.add_all([b1, b2])
        db.commit()
        db.refresh(b1)
        db.refresh(b2)
        return [b1, b2]

    def test_match_author_exact(self, db, sample_authors):
        result = match_author("John Ruskin", db)
        assert result is not None
        assert result["name"] == "John Ruskin"
        assert result["similarity"] == 1.0

    def test_match_author_no_match(self, db, sample_authors):
        result = match_author("William Shakespeare", db)
        assert result is None

    def test_match_binder(self, db, sample_binders):
        # After normalization, "Riviere" matches "Rivière & Son" -> "riviere"
        result = match_binder("Riviere", db)
        assert result is not None
        assert result["name"] == "Rivière & Son"

    def test_match_publisher(self, db, sample_publishers):
        # "Smith Elder" matches "Smith, Elder & Co." after normalization
        result = match_publisher("Smith Elder", db)
        assert result is not None
        assert result["name"] == "Smith, Elder & Co."
