"""Tests for set completion detection service."""

from app.models.author import Author
from app.models.book import Book


class TestRomanToInt:
    """Tests for Roman numeral to integer conversion."""

    def test_roman_i_returns_1(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("I") == 1

    def test_roman_v_returns_5(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("V") == 5

    def test_roman_viii_returns_8(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("VIII") == 8

    def test_roman_xii_returns_12(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("XII") == 12

    def test_roman_iv_returns_4(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("IV") == 4

    def test_roman_ix_returns_9(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("IX") == 9

    def test_roman_lowercase_works(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("viii") == 8

    def test_roman_invalid_returns_none(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("INVALID") is None

    def test_roman_xiii_exceeds_limit_returns_none(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("XIII") is None


class TestExtractVolumeNumber:
    """Tests for extracting volume number from title."""

    def test_vol_dot_arabic(self):
        from app.services.set_detection import extract_volume_number

        assert extract_volume_number("Works Vol. 3") == 3

    def test_vol_no_dot_arabic(self):
        from app.services.set_detection import extract_volume_number

        assert extract_volume_number("Works Vol 12") == 12

    def test_volume_arabic(self):
        from app.services.set_detection import extract_volume_number

        assert extract_volume_number("Complete Works Volume 2") == 2

    def test_volume_roman(self):
        from app.services.set_detection import extract_volume_number

        assert extract_volume_number("Works Volume VIII") == 8

    def test_vol_dot_roman(self):
        from app.services.set_detection import extract_volume_number

        assert extract_volume_number("Works Vol. IV") == 4

    def test_part_arabic(self):
        from app.services.set_detection import extract_volume_number

        assert extract_volume_number("History Part 2") == 2

    def test_no_volume_returns_none(self):
        from app.services.set_detection import extract_volume_number

        assert extract_volume_number("Complete Works") is None

    def test_case_insensitive(self):
        from app.services.set_detection import extract_volume_number

        assert extract_volume_number("works VOLUME viii") == 8

    def test_volume_at_end(self):
        from app.services.set_detection import extract_volume_number

        assert extract_volume_number("Byron Poetical Works, Vol. 5") == 5


class TestNormalizeTitle:
    """Tests for stripping volume indicators from titles."""

    def test_strips_vol_dot_arabic(self):
        from app.services.set_detection import normalize_title

        assert normalize_title("Byron Works Vol. 8") == "Byron Works"

    def test_strips_vol_arabic(self):
        from app.services.set_detection import normalize_title

        assert normalize_title("Works Vol 3") == "Works"

    def test_strips_volume_roman(self):
        from app.services.set_detection import normalize_title

        assert normalize_title("Works, Volume III") == "Works"

    def test_strips_part(self):
        from app.services.set_detection import normalize_title

        assert normalize_title("History Part 2") == "History"

    def test_strips_parenthetical_vols(self):
        from app.services.set_detection import normalize_title

        assert normalize_title("Works (in 3 vols)") == "Works"

    def test_no_volume_unchanged(self):
        from app.services.set_detection import normalize_title

        assert normalize_title("Complete Works") == "Complete Works"

    def test_strips_trailing_whitespace(self):
        from app.services.set_detection import normalize_title

        assert normalize_title("Works Vol. 1  ") == "Works"

    def test_preserves_internal_structure(self):
        from app.services.set_detection import normalize_title

        assert (
            normalize_title("Lord Byron's Complete Poetical Works Vol. 5")
            == "Lord Byron's Complete Poetical Works"
        )


class TestTitlesMatch:
    """Tests for checking if two normalized titles represent the same work."""

    def test_exact_match(self):
        from app.services.set_detection import titles_match

        assert titles_match("Byron Works", "Byron Works") is True

    def test_case_insensitive(self):
        from app.services.set_detection import titles_match

        assert titles_match("Byron Works", "byron works") is True

    def test_subset_a_in_b(self):
        from app.services.set_detection import titles_match

        assert titles_match("Byron Works", "Byron Works Complete") is True

    def test_subset_b_in_a(self):
        from app.services.set_detection import titles_match

        assert titles_match("Byron Works Complete", "Byron Works") is True

    def test_no_match(self):
        from app.services.set_detection import titles_match

        assert titles_match("Byron Works", "Shelley Poems") is False

    def test_whitespace_handling(self):
        from app.services.set_detection import titles_match

        assert titles_match("  Byron Works  ", "Byron Works") is True


class TestDetectSetCompletion:
    """Integration tests for set completion detection."""

    def test_completes_set_true(self, db):
        """Vol 3 completes set when Vols 1, 2, 4 already owned."""
        from app.services.set_detection import detect_set_completion

        # Setup: Create author with Vols 1, 2, 4 of 4-volume set
        author = Author(name="Lord Byron")
        db.add(author)
        db.commit()

        for vol in [1, 2, 4]:
            book = Book(
                title=f"Works Vol. {vol}",
                author_id=author.id,
                volumes=4,
                status="OWNED",
            )
            db.add(book)
        db.commit()

        # Test: Vol 3 completes the set
        result = detect_set_completion(
            db=db,
            author_id=author.id,
            title="Works Vol. 3",
            volumes=1,
        )
        assert result is True

    def test_completes_set_false_not_final(self, db):
        """Vol 3 does NOT complete when only Vols 1, 2 owned (missing 4)."""
        from app.services.set_detection import detect_set_completion

        author = Author(name="Lord Byron")
        db.add(author)
        db.commit()

        for vol in [1, 2]:
            book = Book(
                title=f"Works Vol. {vol}",
                author_id=author.id,
                volumes=4,
                status="OWNED",
            )
            db.add(book)
        db.commit()

        result = detect_set_completion(
            db=db,
            author_id=author.id,
            title="Works Vol. 3",
            volumes=1,
        )
        assert result is False

    def test_completes_set_false_no_matches(self, db):
        """Returns False when no matching books in collection."""
        from app.services.set_detection import detect_set_completion

        author = Author(name="Lord Byron")
        db.add(author)
        db.commit()

        result = detect_set_completion(
            db=db,
            author_id=author.id,
            title="Works Vol. 3",
            volumes=1,
        )
        assert result is False

    def test_completes_set_false_multivolume_record(self, db):
        """Skip detection for multi-volume set as single record."""
        from app.services.set_detection import detect_set_completion

        author = Author(name="Lord Byron")
        db.add(author)
        db.commit()

        # This is a complete 4-volume set, not a single volume
        result = detect_set_completion(
            db=db,
            author_id=author.id,
            title="Complete Works",  # No volume indicator
            volumes=4,  # Multi-volume set
        )
        assert result is False

    def test_excludes_book_id(self, db):
        """Excludes specified book from matching."""
        from app.services.set_detection import detect_set_completion

        author = Author(name="Lord Byron")
        db.add(author)
        db.commit()

        books = []
        for vol in [1, 2, 3, 4]:
            book = Book(
                title=f"Works Vol. {vol}",
                author_id=author.id,
                volumes=4,
                status="OWNED",
            )
            db.add(book)
            books.append(book)
        db.commit()

        # When checking existing book Vol 3, exclude it - still need to own 3 others
        # With 4 volumes total and excluding Vol 3, we have 3 others
        # 3 + 1 = 4 = set size, so it WOULD complete (if we didn't already have it)
        result = detect_set_completion(
            db=db,
            author_id=author.id,
            title="Works Vol. 3",
            volumes=1,
            book_id=books[2].id,  # Exclude Vol 3
        )
        # With Vol 3 excluded, we have Vols 1, 2, 4 - adding Vol 3 completes
        assert result is True

    def test_roman_numeral_volumes(self, db):
        """Handles Roman numeral volume indicators."""
        from app.services.set_detection import detect_set_completion

        author = Author(name="Lord Byron")
        db.add(author)
        db.commit()

        for vol in ["I", "II", "IV"]:
            book = Book(
                title=f"Works Volume {vol}",
                author_id=author.id,
                volumes=4,
                status="OWNED",
            )
            db.add(book)
        db.commit()

        result = detect_set_completion(
            db=db,
            author_id=author.id,
            title="Works Volume III",
            volumes=1,
        )
        assert result is True

    def test_excludes_removed_books(self, db):
        """Excludes books with REMOVED status."""
        from app.services.set_detection import detect_set_completion

        author = Author(name="Lord Byron")
        db.add(author)
        db.commit()

        # Add Vols 1, 2 as OWNED
        for vol in [1, 2]:
            book = Book(
                title=f"Works Vol. {vol}",
                author_id=author.id,
                volumes=4,
                status="OWNED",
            )
            db.add(book)

        # Add Vol 4 as REMOVED - should not count
        removed = Book(
            title="Works Vol. 4",
            author_id=author.id,
            volumes=4,
            status="REMOVED",
        )
        db.add(removed)
        db.commit()

        # Only have Vols 1, 2 (OWNED), adding Vol 3 doesn't complete
        result = detect_set_completion(
            db=db,
            author_id=author.id,
            title="Works Vol. 3",
            volumes=1,
        )
        assert result is False

    def test_no_author_id_returns_false(self, db):
        """Returns False when author_id is None."""
        from app.services.set_detection import detect_set_completion

        result = detect_set_completion(
            db=db,
            author_id=None,
            title="Works Vol. 3",
            volumes=1,
        )
        assert result is False
