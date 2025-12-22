"""Quick test to verify tier labels work correctly."""

from app.services.scoring import calculate_strategic_fit_breakdown


class TestTierLabels:
    """Test that tier labels display correctly in breakdowns."""

    def test_tier_1_label_shows_correctly(self):
        """Tier 1 authors should show 'Tier 1 author (+15)'."""
        breakdown = calculate_strategic_fit_breakdown(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=15,
            volume_count=1,
            author_name="Charles Darwin",
            publisher_name=None,
            binder_name=None,
            author_tier="TIER_1",
        )
        factors_dict = {f.name: f for f in breakdown.factors}
        assert "author_priority" in factors_dict
        assert "Tier 1" in factors_dict["author_priority"].reason
        assert "+15" in factors_dict["author_priority"].reason
        assert "Charles Darwin" in factors_dict["author_priority"].reason

    def test_tier_2_label_shows_correctly(self):
        """Tier 2 authors should show 'Tier 2 author (+10)'."""
        breakdown = calculate_strategic_fit_breakdown(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=10,
            volume_count=1,
            author_name="Charles Dickens",
            publisher_name=None,
            binder_name=None,
            author_tier="TIER_2",
        )
        factors_dict = {f.name: f for f in breakdown.factors}
        assert "author_priority" in factors_dict
        assert "Tier 2" in factors_dict["author_priority"].reason
        assert "+10" in factors_dict["author_priority"].reason
        assert "Charles Dickens" in factors_dict["author_priority"].reason

    def test_tier_3_label_shows_correctly(self):
        """Tier 3 authors should show 'Tier 3 author (+5)'."""
        breakdown = calculate_strategic_fit_breakdown(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=5,
            volume_count=1,
            author_name="John Ruskin",
            publisher_name=None,
            binder_name=None,
            author_tier="TIER_3",
        )
        factors_dict = {f.name: f for f in breakdown.factors}
        assert "author_priority" in factors_dict
        assert "Tier 3" in factors_dict["author_priority"].reason
        assert "+5" in factors_dict["author_priority"].reason
        assert "John Ruskin" in factors_dict["author_priority"].reason

    def test_non_priority_author_label(self):
        """Non-priority authors should show 'not a priority author'."""
        breakdown = calculate_strategic_fit_breakdown(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
            volume_count=1,
            author_name="Unknown Author",
            publisher_name=None,
            binder_name=None,
            author_tier=None,
        )
        factors_dict = {f.name: f for f in breakdown.factors}
        assert "author_priority" in factors_dict
        assert "not a priority author" in factors_dict["author_priority"].reason
        assert "Unknown Author" in factors_dict["author_priority"].reason
