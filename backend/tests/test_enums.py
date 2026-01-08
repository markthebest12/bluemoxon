"""Tests for enum definitions.

Following TDD: These tests are written first, before the implementation.
"""

from app.enums import (
    BookStatus,
    ConditionGrade,
    InventoryType,
    SortOrder,
    Tier,
)


class TestBookStatus:
    """Tests for BookStatus enum."""

    def test_values(self):
        """Verify all BookStatus values are correct."""
        assert BookStatus.EVALUATING == "EVALUATING"
        assert BookStatus.IN_TRANSIT == "IN_TRANSIT"
        assert BookStatus.ON_HAND == "ON_HAND"
        assert BookStatus.REMOVED == "REMOVED"

    def test_all_values_accounted_for(self):
        """Ensure no values are missing from tests."""
        assert len(BookStatus) == 4

    def test_string_serialization(self):
        """StrEnum should serialize to string values."""
        assert str(BookStatus.EVALUATING) == "EVALUATING"
        assert f"{BookStatus.IN_TRANSIT}" == "IN_TRANSIT"


class TestInventoryType:
    """Tests for InventoryType enum."""

    def test_values(self):
        """Verify all InventoryType values are correct."""
        assert InventoryType.PRIMARY == "PRIMARY"
        assert InventoryType.EXTENDED == "EXTENDED"
        assert InventoryType.FLAGGED == "FLAGGED"

    def test_all_values_accounted_for(self):
        """Ensure no values are missing from tests."""
        assert len(InventoryType) == 3

    def test_string_serialization(self):
        """StrEnum should serialize to string values."""
        assert str(InventoryType.PRIMARY) == "PRIMARY"


class TestTier:
    """Tests for Tier enum."""

    def test_values(self):
        """Verify all Tier values are correct."""
        assert Tier.TIER_1 == "TIER_1"
        assert Tier.TIER_2 == "TIER_2"
        assert Tier.TIER_3 == "TIER_3"

    def test_all_values_accounted_for(self):
        """Ensure no values are missing from tests."""
        assert len(Tier) == 3

    def test_string_serialization(self):
        """StrEnum should serialize to string values."""
        assert str(Tier.TIER_1) == "TIER_1"


class TestConditionGrade:
    """Tests for ConditionGrade enum."""

    def test_values(self):
        """Verify all ConditionGrade values are correct."""
        assert ConditionGrade.FINE == "FINE"
        assert ConditionGrade.VERY_GOOD == "VERY_GOOD"
        assert ConditionGrade.GOOD == "GOOD"
        assert ConditionGrade.FAIR == "FAIR"
        assert ConditionGrade.POOR == "POOR"

    def test_all_values_accounted_for(self):
        """Ensure no values are missing from tests."""
        assert len(ConditionGrade) == 5

    def test_string_serialization(self):
        """StrEnum should serialize to string values."""
        assert str(ConditionGrade.VERY_GOOD) == "VERY_GOOD"


class TestSortOrder:
    """Tests for SortOrder enum."""

    def test_values(self):
        """Verify all SortOrder values are correct (lowercase for API)."""
        assert SortOrder.ASC == "asc"
        assert SortOrder.DESC == "desc"

    def test_all_values_accounted_for(self):
        """Ensure no values are missing from tests."""
        assert len(SortOrder) == 2

    def test_string_serialization(self):
        """StrEnum should serialize to string values."""
        assert str(SortOrder.ASC) == "asc"
