"""Scoring engine tests."""

from app.models.author import Author


class TestAuthorPriorityScore:
    """Tests for author priority_score field."""

    def test_author_has_priority_score_field(self, db):
        """Author model should have priority_score field defaulting to 0."""
        author = Author(name="Test Author")
        db.add(author)
        db.commit()
        db.refresh(author)

        assert hasattr(author, "priority_score")
        assert author.priority_score == 0

    def test_author_priority_score_can_be_set(self, db):
        """Author priority_score can be set to custom value."""
        author = Author(name="Thomas Hardy", priority_score=50)
        db.add(author)
        db.commit()
        db.refresh(author)

        assert author.priority_score == 50
