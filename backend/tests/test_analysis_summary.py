"""Tests for analysis summary parsing.

Tests both Napoleon v2 STRUCTURED-DATA format and legacy YAML format.
"""

from app.services.analysis_summary import calculate_value_vs_cost, parse_analysis_summary


class TestParseNapoleonV2Format:
    """Tests for parsing Napoleon v2 STRUCTURED-DATA format."""

    def test_parse_structured_data_block(self):
        """Test extracting Napoleon v2 structured data from analysis."""
        analysis = """---STRUCTURED-DATA---
CONDITION_GRADE: VG+
BINDER_IDENTIFIED: Rivière & Son
BINDER_CONFIDENCE: HIGH
BINDING_TYPE: Full Morocco
VALUATION_LOW: 400
VALUATION_MID: 525
VALUATION_HIGH: 650
ERA_PERIOD: Victorian
PUBLICATION_YEAR: 1882
---END-STRUCTURED-DATA---

# Executive Summary

This is the full analysis content...
"""
        result = parse_analysis_summary(analysis)

        assert result is not None
        assert result["condition_grade"] == "VG+"
        assert result["binder_identified"] == "Rivière & Son"
        assert result["binder_confidence"] == "HIGH"
        assert result["binding_type"] == "Full Morocco"
        assert result["valuation_low"] == 400
        assert result["valuation_mid"] == 525
        assert result["valuation_high"] == 650
        assert result["era_period"] == "Victorian"
        assert result["publication_year"] == 1882

    def test_parse_structured_data_with_dollar_signs(self):
        """Test parsing valuation fields with dollar signs."""
        analysis = """---STRUCTURED-DATA---
VALUATION_LOW: $400
VALUATION_MID: $525
VALUATION_HIGH: $650
CONDITION_GRADE: Good
---END-STRUCTURED-DATA---

# Analysis
"""
        result = parse_analysis_summary(analysis)

        assert result is not None
        assert result["valuation_low"] == 400
        assert result["valuation_mid"] == 525
        assert result["valuation_high"] == 650

    def test_parse_structured_data_skips_placeholder_values(self):
        """Test that placeholder values like [Fine] are skipped."""
        analysis = """---STRUCTURED-DATA---
CONDITION_GRADE: Good
BINDER_IDENTIFIED: UNKNOWN
VALUATION_LOW: 100
VALUATION_HIGH: 200
---END-STRUCTURED-DATA---
"""
        result = parse_analysis_summary(analysis)

        assert result is not None
        assert result["condition_grade"] == "Good"
        assert "binder_identified" not in result  # UNKNOWN should be skipped
        assert result["valuation_low"] == 100

    def test_parse_structured_data_case_insensitive(self):
        """Test that parsing works regardless of case."""
        analysis = """---structured-data---
condition_grade: VG
valuation_low: 100
VALUATION_HIGH: 200
---end-structured-data---
"""
        result = parse_analysis_summary(analysis)

        assert result is not None
        assert result["condition_grade"] == "VG"
        assert result["valuation_low"] == 100
        assert result["valuation_high"] == 200


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
        assert updates["condition_grade"] == "VERY_GOOD"  # Normalized from "Very Good"
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


class TestExtractNapoleonV2Updates:
    """Tests for extracting book updates from Napoleon v2 format."""

    def test_extract_valuation_fields(self):
        """Test that valuation_* fields map to value_* book fields."""
        from decimal import Decimal

        from app.services.analysis_summary import extract_book_updates_from_yaml

        # Napoleon v2 uses valuation_low/mid/high, not estimated_value_*
        yaml_data = {
            "valuation_low": 400,
            "valuation_mid": 525,
            "valuation_high": 650,
            "condition_grade": "Good",
            "binding_type": "Full Morocco",
        }

        updates = extract_book_updates_from_yaml(yaml_data)

        assert updates["value_low"] == Decimal("400")
        assert updates["value_mid"] == Decimal("525")
        assert updates["value_high"] == Decimal("650")
        assert updates["condition_grade"] == "GOOD"  # Normalized from "Good"
        assert updates["binding_type"] == "Full Morocco"

    def test_extract_calculates_mid_when_missing(self):
        """Test that value_mid is calculated if not provided."""
        from decimal import Decimal

        from app.services.analysis_summary import extract_book_updates_from_yaml

        yaml_data = {
            "valuation_low": 400,
            "valuation_high": 600,
            # valuation_mid not provided
        }

        updates = extract_book_updates_from_yaml(yaml_data)

        assert updates["value_low"] == Decimal("400")
        assert updates["value_high"] == Decimal("600")
        assert updates["value_mid"] == Decimal("500")  # Calculated

    def test_extract_prefers_explicit_mid(self):
        """Test that explicit valuation_mid is used over calculated."""
        from decimal import Decimal

        from app.services.analysis_summary import extract_book_updates_from_yaml

        yaml_data = {
            "valuation_low": 400,
            "valuation_mid": 600,  # Explicit, different from (400+800)/2 = 600
            "valuation_high": 800,
        }

        updates = extract_book_updates_from_yaml(yaml_data)

        assert updates["value_mid"] == Decimal("600")  # Uses explicit value

    def test_extract_full_napoleon_v2_workflow(self):
        """Integration test: parse Napoleon v2 and extract book updates."""
        from decimal import Decimal

        from app.services.analysis_summary import (
            extract_book_updates_from_yaml,
            parse_analysis_summary,
        )

        analysis = """---STRUCTURED-DATA---
CONDITION_GRADE: VG+
BINDING_TYPE: Full Morocco
VALUATION_LOW: 400
VALUATION_MID: 525
VALUATION_HIGH: 650
---END-STRUCTURED-DATA---

# Executive Summary

Darwin's Descent of Man analysis...
"""
        parsed = parse_analysis_summary(analysis)
        updates = extract_book_updates_from_yaml(parsed)

        assert updates["value_low"] == Decimal("400")
        assert updates["value_mid"] == Decimal("525")
        assert updates["value_high"] == Decimal("650")
        assert updates["condition_grade"] == "NEAR_FINE"  # Normalized from "VG+"
        assert updates["binding_type"] == "Full Morocco"
