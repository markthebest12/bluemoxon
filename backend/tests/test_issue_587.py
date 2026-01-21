"""TDD tests for Issue #587 (volume scoring).

These tests are written FIRST (RED phase) to define expected behavior.
Implementation comes after tests fail.
"""

from app.services.scoring import (
    calculate_strategic_fit,
    calculate_strategic_fit_breakdown,
)


class TestIssue587_VolumeScoring:
    """Issue #587: Remove negative scoring impact for multi-volume sets.

    Current behavior: -10 for 4 volumes, -20 for 5+ volumes
    Expected behavior: 0 for all volume counts, but NOTED in breakdown
    """

    def test_four_volume_set_no_penalty(self):
        """4-volume set should NOT subtract points (changed from -10 to 0)."""
        score = calculate_strategic_fit(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
            volume_count=4,
        )
        # Issue #587: Should be 0, not -10
        assert score == 0

    def test_five_volume_set_no_penalty(self):
        """5-volume set should NOT subtract points (changed from -20 to 0)."""
        score = calculate_strategic_fit(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
            volume_count=5,
        )
        # Issue #587: Should be 0, not -20
        assert score == 0

    def test_six_plus_volume_set_no_penalty(self):
        """6+ volume set should NOT subtract points (changed from -20 to 0)."""
        score = calculate_strategic_fit(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
            volume_count=8,
        )
        # Issue #587: Should be 0, not -20
        assert score == 0

    def test_combined_factors_without_volume_penalty(self):
        """Combined factors should NOT include volume penalty."""
        score = calculate_strategic_fit(
            publisher_tier="TIER_1",  # +35
            binder_tier="TIER_1",  # +40 + 15 (DOUBLE TIER 1)
            year_start=1867,  # +20 (Victorian)
            is_complete=True,  # +15
            condition_grade="VERY_GOOD",  # +15 (enum value, not display label)
            author_priority_score=50,  # +50
            volume_count=4,  # Should be 0 now, not -10
        )
        # 35 + 40 + 15 + 20 + 15 + 15 + 50 + 0 = 190 (was 180 with -10 penalty)
        assert score == 190

    def test_breakdown_notes_large_set_without_penalty(self):
        """Breakdown should NOTE large sets but with 0 points, not negative."""
        breakdown = calculate_strategic_fit_breakdown(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
            volume_count=6,
        )

        # Find the volume-related factor
        volume_factors = [f for f in breakdown.factors if "volume" in f.name.lower()]
        assert len(volume_factors) == 1, "Should have exactly one volume factor"

        factor = volume_factors[0]
        # Issue #587: Should be 0 points, not -20
        assert factor.points == 0
        # Should still note the storage consideration
        assert "6" in factor.reason or "volume" in factor.reason.lower()

    def test_breakdown_notes_four_volume_without_penalty(self):
        """4-volume breakdown should note issue with 0 points."""
        breakdown = calculate_strategic_fit_breakdown(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
            volume_count=4,
        )

        factors_dict = {f.name: f for f in breakdown.factors}

        # Should NOT have volume_penalty factor (which implies negative points)
        assert "volume_penalty" not in factors_dict

        # Should have volume_count factor with 0 points noting the consideration
        assert "volume_count" in factors_dict
        assert factors_dict["volume_count"].points == 0
