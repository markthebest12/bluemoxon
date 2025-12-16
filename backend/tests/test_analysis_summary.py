"""Tests for analysis summary YAML parsing."""

from app.services.analysis_summary import calculate_value_vs_cost, parse_analysis_summary


class TestParseAnalysisSummary:
    """Tests for parsing YAML summary block from analysis markdown."""

    def test_parse_valid_yaml_summary(self):
        """Test extracting YAML summary from analysis with valid block."""
        analysis = """## SUMMARY
---
title: "The Stones of Venice"
author: "John Ruskin"
publisher: "Smith, Elder & Co."
edition: "First edition"
publication_year: "1851-1853"
volumes: 3
binder: "Rivière & Son"
binding_type: "Full morocco"
condition_grade: "Very Good"
provenance: "Ex-libris John Smith; later private collection"
estimated_value_low: 2500
estimated_value_high: 3500
currency: "USD"
acquisition_cost: 142.41
value_vs_cost: "40-53% below FMV"
summary: "First edition of Ruskin's influential architectural treatise."
---

## 1. Executive Summary

This is the full analysis content...
"""
        result = parse_analysis_summary(analysis)

        assert result is not None
        assert result["title"] == "The Stones of Venice"
        assert result["author"] == "John Ruskin"
        assert result["publisher"] == "Smith, Elder & Co."
        assert result["edition"] == "First edition"
        assert result["publication_year"] == "1851-1853"
        assert result["volumes"] == 3
        assert result["binder"] == "Rivière & Son"
        assert result["binding_type"] == "Full morocco"
        assert result["condition_grade"] == "Very Good"
        assert result["provenance"] == "Ex-libris John Smith; later private collection"
        assert result["estimated_value_low"] == 2500
        assert result["estimated_value_high"] == 3500
        assert result["currency"] == "USD"
        assert result["acquisition_cost"] == 142.41
        assert result["value_vs_cost"] == "40-53% below FMV"
        assert "Ruskin" in result["summary"]

    def test_parse_summary_no_yaml_block(self):
        """Test returns None when no YAML summary present."""
        analysis = """## 1. Executive Summary

This is analysis without a YAML summary block.

## 2. Condition Assessment

More content here...
"""
        result = parse_analysis_summary(analysis)
        assert result is None

    def test_parse_summary_null_values(self):
        """Test handling null/missing values in YAML."""
        analysis = """## SUMMARY
---
title: "Unknown Book"
author: null
publisher: null
binder: null
estimated_value_low: 100
estimated_value_high: 200
---

## Content
"""
        result = parse_analysis_summary(analysis)

        assert result is not None
        assert result["title"] == "Unknown Book"
        assert result["author"] is None
        assert result["publisher"] is None
        assert result["binder"] is None

    def test_parse_summary_multiline_values(self):
        """Test handling multiline values like provenance."""
        analysis = """## SUMMARY
---
title: "Test Book"
provenance: "Originally from the library of Lord Byron; later acquired by Thomas Moore; sold at Sotheby's 1920"
summary: "A significant copy with exceptional provenance tracing through major literary figures of the Romantic period."
---

## Content
"""
        result = parse_analysis_summary(analysis)

        assert result is not None
        assert "Lord Byron" in result["provenance"]
        assert "Thomas Moore" in result["provenance"]
        assert "Sotheby's" in result["provenance"]


class TestCalculateValueVsCost:
    """Tests for value vs cost calculation."""

    def test_calculate_below_fmv(self):
        """Test calculating percentage below FMV."""
        # Midpoint = 3000, cost = 1500 -> 50% below FMV
        result = calculate_value_vs_cost(
            acquisition_cost=1500.0,
            estimated_value_low=2500,
            estimated_value_high=3500,
        )
        assert result == "50% below FMV"

    def test_calculate_above_fmv(self):
        """Test calculating percentage above FMV."""
        # Midpoint = 1000, cost = 1500 -> 50% above FMV
        result = calculate_value_vs_cost(
            acquisition_cost=1500.0,
            estimated_value_low=800,
            estimated_value_high=1200,
        )
        assert result == "50% above FMV"

    def test_calculate_at_fmv(self):
        """Test when acquisition cost equals FMV."""
        result = calculate_value_vs_cost(
            acquisition_cost=1000.0,
            estimated_value_low=800,
            estimated_value_high=1200,
        )
        assert result == "At FMV"

    def test_calculate_range_format(self):
        """Test range format when low/high differ significantly."""
        # Midpoint = 3000, (3000-142.41)/3000 = 95% below FMV
        result = calculate_value_vs_cost(
            acquisition_cost=142.41,
            estimated_value_low=2500,
            estimated_value_high=3500,
        )
        # Should be approximately 95% below FMV
        assert "below FMV" in result
        assert "95%" in result

    def test_calculate_missing_values(self):
        """Test returns None when values missing."""
        result = calculate_value_vs_cost(
            acquisition_cost=None,
            estimated_value_low=2500,
            estimated_value_high=3500,
        )
        assert result is None

        result = calculate_value_vs_cost(
            acquisition_cost=100.0,
            estimated_value_low=None,
            estimated_value_high=None,
        )
        assert result is None


class TestExtractBookUpdates:
    """Tests for extracting book field updates from YAML summary."""

    def test_extract_basic_values(self):
        """Test extracting value estimates from YAML."""
        from decimal import Decimal

        from app.services.analysis_summary import extract_book_updates_from_yaml

        yaml_data = {
            "estimated_value_low": 35,
            "estimated_value_high": 65,
            "condition_grade": "Very Good",
            "acquisition_cost": 20.00,
            "provenance": "From library of John Smith",
        }

        updates = extract_book_updates_from_yaml(yaml_data)

        assert updates["value_low"] == Decimal("35")
        assert updates["value_high"] == Decimal("65")
        assert updates["value_mid"] == Decimal("50")  # (35 + 65) / 2
        assert updates["condition_grade"] == "Very Good"
        assert updates["acquisition_cost"] == Decimal("20.00")
        assert updates["provenance"] == "From library of John Smith"

    def test_extract_handles_missing_values(self):
        """Test that missing YAML values don't create updates."""
        from app.services.analysis_summary import extract_book_updates_from_yaml

        yaml_data = {
            "title": "Test Book",
            "estimated_value_low": 100,
            # estimated_value_high missing
            # condition_grade missing
        }

        updates = extract_book_updates_from_yaml(yaml_data)

        assert updates["value_low"] == 100
        assert "value_high" not in updates
        assert "value_mid" not in updates  # Can't calculate without both
        assert "condition_grade" not in updates

    def test_extract_handles_null_values(self):
        """Test that null YAML values don't create updates."""
        from app.services.analysis_summary import extract_book_updates_from_yaml

        yaml_data = {
            "estimated_value_low": 100,
            "estimated_value_high": 200,
            "provenance": None,
            "binder": None,
        }

        updates = extract_book_updates_from_yaml(yaml_data)

        assert updates["value_low"] == 100
        assert updates["value_high"] == 200
        assert "provenance" not in updates
        assert "binder" not in updates

    def test_extract_calculates_value_mid(self):
        """Test that value_mid is calculated from low and high."""
        from decimal import Decimal

        from app.services.analysis_summary import extract_book_updates_from_yaml

        yaml_data = {
            "estimated_value_low": 100,
            "estimated_value_high": 300,
        }

        updates = extract_book_updates_from_yaml(yaml_data)

        assert updates["value_mid"] == Decimal("200")  # (100 + 300) / 2

    def test_extract_empty_yaml(self):
        """Test that empty YAML returns empty updates."""
        from app.services.analysis_summary import extract_book_updates_from_yaml

        updates = extract_book_updates_from_yaml({})
        assert updates == {}

        updates = extract_book_updates_from_yaml(None)
        assert updates == {}
