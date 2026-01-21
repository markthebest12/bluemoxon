"""Tests for tiered recommendation scoring."""

from decimal import Decimal


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
        """FINE/NEAR_FINE condition should add 15 points (enum values, not display labels)."""
        from app.services.tiered_scoring import calculate_quality_score

        for grade in ["FINE", "NEAR_FINE"]:
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
        """VERY_GOOD/GOOD condition should add 10 points (enum values, not display labels)."""
        from app.services.tiered_scoring import calculate_quality_score

        for grade in ["VERY_GOOD", "GOOD"]:
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

    def test_large_volume_no_penalty(self):
        """5+ volumes should NOT subtract points (Issue #587)."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier="TIER_1",  # +25
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=6,  # 0 (noted but no penalty per Issue #587)
            is_duplicate=False,
        )
        assert score == 25  # 25 + 0

    def test_max_quality_score_is_100(self):
        """Quality score should cap at 100."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier="TIER_1",  # +25
            binder_tier="TIER_1",  # +30 + 10 bonus = 40
            year_start=1867,  # +15
            condition_grade="FINE",  # +15 (enum value)
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


class TestRecommendationMatrix:
    """Tests for recommendation matrix with floor rules."""

    def test_high_score_excellent_price_strong_buy(self):
        """Score >= 80 + EXCELLENT price = STRONG_BUY."""
        from app.services.tiered_scoring import determine_recommendation_tier

        tier = determine_recommendation_tier(
            combined_score=85,
            price_position="EXCELLENT",
            quality_score=80,
            strategic_fit_score=80,
        )
        assert tier == "STRONG_BUY"

    def test_high_score_poor_price_conditional(self):
        """Score >= 80 + POOR price = CONDITIONAL."""
        from app.services.tiered_scoring import determine_recommendation_tier

        tier = determine_recommendation_tier(
            combined_score=85,
            price_position="POOR",
            quality_score=80,
            strategic_fit_score=80,
        )
        assert tier == "CONDITIONAL"

    def test_low_score_excellent_price_buy(self):
        """Score 40-59 + EXCELLENT price = BUY."""
        from app.services.tiered_scoring import determine_recommendation_tier

        tier = determine_recommendation_tier(
            combined_score=50,
            price_position="EXCELLENT",
            quality_score=50,
            strategic_fit_score=50,
        )
        assert tier == "BUY"

    def test_low_score_fair_price_pass(self):
        """Score 40-59 + FAIR price = PASS."""
        from app.services.tiered_scoring import determine_recommendation_tier

        tier = determine_recommendation_tier(
            combined_score=50,
            price_position="FAIR",
            quality_score=50,
            strategic_fit_score=50,
        )
        assert tier == "PASS"

    def test_strategic_fit_floor_caps_at_conditional(self):
        """Strategic fit < 30 should cap at CONDITIONAL regardless of matrix."""
        from app.services.tiered_scoring import determine_recommendation_tier

        # Would be STRONG_BUY without floor
        tier = determine_recommendation_tier(
            combined_score=85,
            price_position="EXCELLENT",
            quality_score=100,
            strategic_fit_score=20,  # Below 30 floor
        )
        assert tier == "CONDITIONAL"

    def test_quality_floor_caps_at_conditional(self):
        """Quality < 40 should cap at CONDITIONAL regardless of matrix."""
        from app.services.tiered_scoring import determine_recommendation_tier

        # Would be BUY without floor
        tier = determine_recommendation_tier(
            combined_score=60,
            price_position="EXCELLENT",
            quality_score=30,  # Below 40 floor
            strategic_fit_score=100,
        )
        assert tier == "CONDITIONAL"

    def test_no_price_position_uses_fair(self):
        """Missing price position should default to FAIR behavior."""
        from app.services.tiered_scoring import determine_recommendation_tier

        tier = determine_recommendation_tier(
            combined_score=75,
            price_position=None,
            quality_score=75,
            strategic_fit_score=75,
        )
        assert tier == "CONDITIONAL"  # 60-79 + FAIR = CONDITIONAL


class TestSuggestedOffer:
    """Tests for suggested offer price calculation."""

    def test_high_combined_score_15_percent_discount(self):
        """Score 70-79 should target 15% below FMV."""
        from app.services.tiered_scoring import calculate_suggested_offer

        offer = calculate_suggested_offer(
            combined_score=75,
            fmv_mid=Decimal("100"),
            strategic_floor_applied=False,
            quality_floor_applied=False,
        )
        assert offer == Decimal("85")  # 100 * 0.85

    def test_medium_combined_score_25_percent_discount(self):
        """Score 60-69 should target 25% below FMV."""
        from app.services.tiered_scoring import calculate_suggested_offer

        offer = calculate_suggested_offer(
            combined_score=65,
            fmv_mid=Decimal("100"),
            strategic_floor_applied=False,
            quality_floor_applied=False,
        )
        assert offer == Decimal("75")  # 100 * 0.75

    def test_low_combined_score_35_percent_discount(self):
        """Score 50-59 should target 35% below FMV."""
        from app.services.tiered_scoring import calculate_suggested_offer

        offer = calculate_suggested_offer(
            combined_score=55,
            fmv_mid=Decimal("100"),
            strategic_floor_applied=False,
            quality_floor_applied=False,
        )
        assert offer == Decimal("65")  # 100 * 0.65

    def test_strategic_floor_40_percent_discount(self):
        """Strategic floor triggered should use 40% discount."""
        from app.services.tiered_scoring import calculate_suggested_offer

        offer = calculate_suggested_offer(
            combined_score=85,  # Would normally be 15%
            fmv_mid=Decimal("100"),
            strategic_floor_applied=True,
            quality_floor_applied=False,
        )
        assert offer == Decimal("60")  # 100 * 0.60

    def test_quality_floor_50_percent_discount(self):
        """Quality floor triggered should use 50% discount."""
        from app.services.tiered_scoring import calculate_suggested_offer

        offer = calculate_suggested_offer(
            combined_score=70,
            fmv_mid=Decimal("100"),
            strategic_floor_applied=False,
            quality_floor_applied=True,
        )
        assert offer == Decimal("50")  # 100 * 0.50

    def test_no_fmv_returns_none(self):
        """Missing FMV should return None."""
        from app.services.tiered_scoring import calculate_suggested_offer

        offer = calculate_suggested_offer(
            combined_score=75,
            fmv_mid=None,
            strategic_floor_applied=False,
            quality_floor_applied=False,
        )
        assert offer is None


class TestReasoningGeneration:
    """Tests for templated reasoning generation."""

    def test_strong_buy_reasoning(self):
        """STRONG_BUY should include quality driver and discount."""
        from app.services.tiered_scoring import generate_reasoning

        reasoning = generate_reasoning(
            recommendation_tier="STRONG_BUY",
            quality_score=90,
            strategic_fit_score=80,
            price_position="EXCELLENT",
            discount_percent=45,
            publisher_name="Bentley",
            binder_name=None,
            author_name="Wilkie Collins",
            strategic_floor_applied=False,
            quality_floor_applied=False,
        )
        assert "STRONG_BUY" not in reasoning  # Tier not repeated in text
        assert "45%" in reasoning or "45" in reasoning
        assert "Bentley" in reasoning or "Collins" in reasoning

    def test_conditional_strategic_floor_reasoning(self):
        """Strategic floor CONDITIONAL should explain wrong publisher."""
        from app.services.tiered_scoring import generate_reasoning

        reasoning = generate_reasoning(
            recommendation_tier="CONDITIONAL",
            quality_score=70,
            strategic_fit_score=15,
            price_position="EXCELLENT",
            discount_percent=60,
            publisher_name="Tauchnitz",
            binder_name=None,
            author_name="Wilkie Collins",
            strategic_floor_applied=True,
            quality_floor_applied=False,
        )
        assert "wrong publisher" in reasoning.lower() or "strategic" in reasoning.lower()

    def test_pass_reasoning(self):
        """PASS should explain primary issue."""
        from app.services.tiered_scoring import generate_reasoning

        reasoning = generate_reasoning(
            recommendation_tier="PASS",
            quality_score=30,
            strategic_fit_score=20,
            price_position="POOR",
            discount_percent=-15,
            publisher_name=None,
            binder_name=None,
            author_name=None,
            strategic_floor_applied=False,
            quality_floor_applied=False,
        )
        assert len(reasoning) > 0
        assert "above fmv" in reasoning.lower() or "overpriced" in reasoning.lower()


class TestPreferredBonus:
    """Tests for preferred entity bonus in quality score."""

    def test_preferred_bonus_constant_exists(self):
        """PREFERRED_BONUS constant should be defined as 10."""
        from app.services.tiered_scoring import PREFERRED_BONUS

        assert PREFERRED_BONUS == 10

    def test_preferred_author_adds_10(self):
        """Preferred author should add 10 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
            author_preferred=True,
            publisher_preferred=False,
            binder_preferred=False,
        )
        assert score == 10

    def test_non_preferred_author_no_bonus(self):
        """Non-preferred author should not add bonus."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
            author_preferred=False,
            publisher_preferred=False,
            binder_preferred=False,
        )
        assert score == 0

    def test_preferred_publisher_adds_10(self):
        """Preferred publisher should add 10 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
            author_preferred=False,
            publisher_preferred=True,
            binder_preferred=False,
        )
        assert score == 10

    def test_preferred_binder_adds_10(self):
        """Preferred binder should add 10 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
            author_preferred=False,
            publisher_preferred=False,
            binder_preferred=True,
        )
        assert score == 10

    def test_all_preferred_entities_stack(self):
        """All three preferred entities should add 30 points total."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
            author_preferred=True,
            publisher_preferred=True,
            binder_preferred=True,
        )
        assert score == 30

    def test_preferred_combines_with_tier_bonuses(self):
        """Preferred bonus should combine with tier bonuses."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier="TIER_1",  # +25
            binder_tier="TIER_1",  # +30 + 10 double bonus
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
            author_preferred=True,  # +10
            publisher_preferred=True,  # +10
            binder_preferred=True,  # +10
        )
        # 25 + 30 + 10 (double) + 10 + 10 + 10 = 95
        assert score == 95
