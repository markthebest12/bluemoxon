"""Tests for tiered recommendation scoring."""

from decimal import Decimal

import pytest


class TestQualityScore:
    """Tests for quality score calculation (0-100)."""

    def test_tier_1_publisher_adds_25(self):
        """Tier 1 publisher should add 25 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier="TIER_1",
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
        )
        assert score == 25

    def test_tier_2_publisher_adds_10(self):
        """Tier 2 publisher should add 10 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier="TIER_2",
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
        )
        assert score == 10

    def test_tier_1_binder_adds_30(self):
        """Tier 1 binder should add 30 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier="TIER_1",
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
        )
        assert score == 30

    def test_tier_2_binder_adds_15(self):
        """Tier 2 binder should add 15 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier="TIER_2",
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
        )
        assert score == 15

    def test_double_tier_1_bonus_adds_10(self):
        """Both publisher AND binder Tier 1 should add bonus 10 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier="TIER_1",  # +25
            binder_tier="TIER_1",  # +30 + 10 bonus
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
        )
        assert score == 65  # 25 + 30 + 10

    def test_victorian_era_adds_15(self):
        """Victorian era (1837-1901) should add 15 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=1867,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
        )
        assert score == 15

    def test_romantic_era_adds_15(self):
        """Romantic era (1800-1836) should add 15 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=1820,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
        )
        assert score == 15

    def test_fine_condition_adds_15(self):
        """Fine/VG+ condition should add 15 points."""
        from app.services.tiered_scoring import calculate_quality_score

        for grade in ["Fine", "VG+"]:
            score = calculate_quality_score(
                publisher_tier=None,
                binder_tier=None,
                year_start=None,
                condition_grade=grade,
                is_complete=False,
                author_priority_score=0,
                volume_count=1,
                is_duplicate=False,
            )
            assert score == 15, f"Failed for grade: {grade}"

    def test_good_condition_adds_10(self):
        """Good condition should add 10 points."""
        from app.services.tiered_scoring import calculate_quality_score

        for grade in ["Good", "VG", "Very Good", "Good+"]:
            score = calculate_quality_score(
                publisher_tier=None,
                binder_tier=None,
                year_start=None,
                condition_grade=grade,
                is_complete=False,
                author_priority_score=0,
                volume_count=1,
                is_duplicate=False,
            )
            assert score == 10, f"Failed for grade: {grade}"

    def test_complete_set_adds_10(self):
        """Complete set should add 10 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=True,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
        )
        assert score == 10

    def test_author_priority_capped_at_15(self):
        """Author priority score should be capped at 15."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=50,  # Should cap at 15
            volume_count=1,
            is_duplicate=False,
        )
        assert score == 15

    def test_duplicate_penalty_minus_30(self):
        """Duplicate title should subtract 30 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier="TIER_1",  # +25
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=True,  # -30
        )
        assert score == 0  # 25 - 30 = -5, floored at 0

    def test_large_volume_penalty_minus_10(self):
        """5+ volumes should subtract 10 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier="TIER_1",  # +25
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=6,  # -10
            is_duplicate=False,
        )
        assert score == 15  # 25 - 10

    def test_max_quality_score_is_100(self):
        """Quality score should cap at 100."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier="TIER_1",  # +25
            binder_tier="TIER_1",  # +30 + 10 bonus = 40
            year_start=1867,  # +15
            condition_grade="Fine",  # +15
            is_complete=True,  # +10
            author_priority_score=50,  # +15 (capped)
            volume_count=1,
            is_duplicate=False,
        )
        # 25 + 40 + 15 + 15 + 10 + 15 = 120, capped at 100
        assert score == 100

    def test_quality_score_floors_at_zero(self):
        """Quality score should not go below 0."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=True,  # -30
        )
        assert score == 0
