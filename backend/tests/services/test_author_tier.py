"""Tests for author tier scoring."""

from app.services.scoring import author_tier_to_score


class TestAuthorTierToScore:
    """Test author tier to score conversion."""

    def test_tier_1_returns_15(self):
        assert author_tier_to_score("TIER_1") == 15

    def test_tier_2_returns_10(self):
        assert author_tier_to_score("TIER_2") == 10

    def test_tier_3_returns_5(self):
        assert author_tier_to_score("TIER_3") == 5

    def test_none_returns_0(self):
        assert author_tier_to_score(None) == 0

    def test_unknown_tier_returns_0(self):
        assert author_tier_to_score("OTHER") == 0
        assert author_tier_to_score("INVALID") == 0
