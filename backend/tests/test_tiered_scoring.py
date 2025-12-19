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


class TestStrategicFitScore:
    """Tests for strategic fit score calculation (0-100)."""

    def test_publisher_matches_author_requirement_adds_40(self):
        """Right publisher for author should add 40 points."""
        from app.services.tiered_scoring import calculate_strategic_fit_score

        score = calculate_strategic_fit_score(
            publisher_matches_author_requirement=True,
            author_book_count=5,
            completes_set=False,
        )
        assert score == 40

    def test_new_author_adds_30(self):
        """New author to collection should add 30 points."""
        from app.services.tiered_scoring import calculate_strategic_fit_score

        score = calculate_strategic_fit_score(
            publisher_matches_author_requirement=False,
            author_book_count=0,
            completes_set=False,
        )
        assert score == 30

    def test_second_author_work_adds_15(self):
        """Second work by author should add 15 points."""
        from app.services.tiered_scoring import calculate_strategic_fit_score

        score = calculate_strategic_fit_score(
            publisher_matches_author_requirement=False,
            author_book_count=1,
            completes_set=False,
        )
        assert score == 15

    def test_completes_set_adds_25(self):
        """Completing a set should add 25 points."""
        from app.services.tiered_scoring import calculate_strategic_fit_score

        score = calculate_strategic_fit_score(
            publisher_matches_author_requirement=False,
            author_book_count=5,
            completes_set=True,
        )
        assert score == 25

    def test_combined_strategic_factors(self):
        """All strategic factors should combine."""
        from app.services.tiered_scoring import calculate_strategic_fit_score

        score = calculate_strategic_fit_score(
            publisher_matches_author_requirement=True,  # +40
            author_book_count=0,  # +30
            completes_set=True,  # +25
        )
        assert score == 95  # 40 + 30 + 25

    def test_strategic_fit_caps_at_100(self):
        """Strategic fit should cap at 100."""
        from app.services.tiered_scoring import calculate_strategic_fit_score

        # Even with maximum factors, cap at 100
        score = calculate_strategic_fit_score(
            publisher_matches_author_requirement=True,  # +40
            author_book_count=0,  # +30
            completes_set=True,  # +25
        )
        assert score <= 100

    def test_strategic_fit_floors_at_zero(self):
        """Strategic fit should not go below 0."""
        from app.services.tiered_scoring import calculate_strategic_fit_score

        score = calculate_strategic_fit_score(
            publisher_matches_author_requirement=False,
            author_book_count=10,  # No bonus
            completes_set=False,
        )
        assert score == 0


class TestPricePosition:
    """Tests for price position calculation."""

    def test_excellent_price_under_70_percent(self):
        """Price < 70% FMV should be EXCELLENT."""
        from app.services.tiered_scoring import calculate_price_position

        position = calculate_price_position(
            asking_price=Decimal("60"),
            fmv_mid=Decimal("100"),
        )
        assert position == "EXCELLENT"

    def test_good_price_70_to_85_percent(self):
        """Price 70-85% FMV should be GOOD."""
        from app.services.tiered_scoring import calculate_price_position

        position = calculate_price_position(
            asking_price=Decimal("75"),
            fmv_mid=Decimal("100"),
        )
        assert position == "GOOD"

    def test_fair_price_85_to_100_percent(self):
        """Price 85-100% FMV should be FAIR."""
        from app.services.tiered_scoring import calculate_price_position

        position = calculate_price_position(
            asking_price=Decimal("95"),
            fmv_mid=Decimal("100"),
        )
        assert position == "FAIR"

    def test_poor_price_over_100_percent(self):
        """Price > 100% FMV should be POOR."""
        from app.services.tiered_scoring import calculate_price_position

        position = calculate_price_position(
            asking_price=Decimal("120"),
            fmv_mid=Decimal("100"),
        )
        assert position == "POOR"

    def test_no_fmv_returns_none(self):
        """Missing FMV should return None."""
        from app.services.tiered_scoring import calculate_price_position

        position = calculate_price_position(
            asking_price=Decimal("100"),
            fmv_mid=None,
        )
        assert position is None


class TestCombinedScore:
    """Tests for combined score calculation."""

    def test_combined_score_weights(self):
        """Combined score should weight quality 60%, strategic fit 40%."""
        from app.services.tiered_scoring import calculate_combined_score

        combined = calculate_combined_score(
            quality_score=100,
            strategic_fit_score=0,
        )
        assert combined == 60  # 100 * 0.6 + 0 * 0.4

        combined = calculate_combined_score(
            quality_score=0,
            strategic_fit_score=100,
        )
        assert combined == 40  # 0 * 0.6 + 100 * 0.4

    def test_combined_score_balanced(self):
        """Balanced scores should average correctly."""
        from app.services.tiered_scoring import calculate_combined_score

        combined = calculate_combined_score(
            quality_score=80,
            strategic_fit_score=80,
        )
        assert combined == 80  # 80 * 0.6 + 80 * 0.4
