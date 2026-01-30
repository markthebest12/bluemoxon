"""Tests for narrative trigger classification."""

from app.services.narrative_classifier import classify_connection


class TestClassifyConnection:
    def test_cross_era_bridge(self):
        result = classify_connection(
            source_era="romantic",
            target_era="victorian",
            source_years=(1788, 1824),
            target_years=(1809, 1882),
            connection_type="publisher",
            source_connection_count=2,
            has_relationship_story=False,
        )
        assert result == "cross_era_bridge"

    def test_social_circle_with_relationship_story(self):
        result = classify_connection(
            source_era="romantic",
            target_era="romantic",
            source_years=(1806, 1861),
            target_years=(1812, 1889),
            connection_type="shared_publisher",
            source_connection_count=3,
            has_relationship_story=True,
        )
        assert result == "social_circle"

    def test_hub_figure(self):
        result = classify_connection(
            source_era="victorian",
            target_era="victorian",
            source_years=(1812, 1870),
            target_years=(None, None),
            connection_type="publisher",
            source_connection_count=8,
            has_relationship_story=False,
        )
        assert result == "hub_figure"

    def test_no_trigger(self):
        result = classify_connection(
            source_era="victorian",
            target_era="victorian",
            source_years=(1850, 1900),
            target_years=(1860, 1910),
            connection_type="publisher",
            source_connection_count=2,
            has_relationship_story=False,
        )
        assert result is None

    def test_cross_era_priority_over_social(self):
        """Cross-era bridge takes priority over social circle."""
        result = classify_connection(
            source_era="romantic",
            target_era="edwardian",
            source_years=(1788, 1824),
            target_years=(1850, 1920),
            connection_type="publisher",
            source_connection_count=2,
            has_relationship_story=True,
        )
        assert result == "cross_era_bridge"

    def test_same_era_not_cross_era(self):
        result = classify_connection(
            source_era="victorian",
            target_era="victorian",
            source_years=(1812, 1870),
            target_years=(1815, 1882),
            connection_type="publisher",
            source_connection_count=2,
            has_relationship_story=False,
        )
        assert result is None

    def test_missing_eras_not_cross_era(self):
        result = classify_connection(
            source_era=None,
            target_era="victorian",
            source_years=(None, None),
            target_years=(1812, 1870),
            connection_type="publisher",
            source_connection_count=2,
            has_relationship_story=False,
        )
        assert result is None
