"""Tests for markdown analysis parser."""

from app.utils.markdown_parser import (
    ParsedAnalysis,
    _extract_sections,
    _parse_condition_assessment,
    _parse_market_analysis,
    parse_analysis_markdown,
)

SAMPLE_MARKDOWN = """# The Ethics of the Dust by John Ruskin (George Allen, 1883)

## Executive Summary

Victorian trade binding in half morocco of Ruskin's dialogues on crystallography. Second Ruskin in collection after Ariadne Florentina. Acquired at slight premium over mid-estimate value.

**Fair Market Value: $40-$80 (mid: $60)**
**Purchase Price: $70.25 (GBP 54.83)**
**Discount/Premium: -17% (slight premium)**
**Status: IN_TRANSIT**

---

## I. HISTORICAL & CULTURAL SIGNIFICANCE

### Author: John Ruskin (1819-1900)

John Ruskin stands as the preeminent Victorian art critic and social thinker. His influence extended from art criticism to architecture, geology, and social reform.

### The Work

"The Ethics of the Dust" represents Ruskin's unique approach to science education.

---

## II. PHYSICAL DESCRIPTION

### Binding
- **Type:** Half morocco (trade binding)
- **Spine:** Dark brown/black morocco with gilt floral tooling
- **Bands:** Raised bands
- **Boards:** Wave comb marbled paper
- **Style:** Victorian trade half binding, competent commercial work

### Condition
- **Grade:** Good
- **Notes:** Typical wear consistent with age; spine gilt bright; boards attached

---

## III. MARKET ANALYSIS

### Comparable Sales
Victorian half morocco Ruskin typically trades at $40-$100 depending on title and condition.

### Valuation
| Metric | Value |
|--------|-------|
| Low | $40 |
| Mid | $60 |
| High | $80 |

### Purchase Analysis
- **Paid:** $70.25 (GBP 54.83)
- **vs. Mid:** +17% premium
- **Assessment:** Slightly above market

---

## IV. COLLECTION INTEGRATION

### Ruskin Holdings
1. **Ariadne Florentina** (Zaehnsdorf, 1890) - $246
2. **The Ethics of the Dust** (George Allen, 1883) - $70

---

## V. RECOMMENDATIONS

**Status:** ACQUIRED

The slight premium over mid-estimate is acceptable for author depth building.

---

## Source Data

- **eBay Item:** 357943004940
"""


class TestParseAnalysisMarkdown:
    """Test the main parsing function."""

    def test_parses_executive_summary(self):
        result = parse_analysis_markdown(SAMPLE_MARKDOWN)
        assert result.executive_summary is not None
        assert "Victorian trade binding" in result.executive_summary
        assert "half morocco" in result.executive_summary

    def test_parses_historical_significance(self):
        result = parse_analysis_markdown(SAMPLE_MARKDOWN)
        assert result.historical_significance is not None
        assert "John Ruskin" in result.historical_significance
        assert "Victorian art critic" in result.historical_significance

    def test_parses_condition_assessment(self):
        result = parse_analysis_markdown(SAMPLE_MARKDOWN)
        assert result.condition_assessment is not None
        assert isinstance(result.condition_assessment, dict)
        assert result.condition_assessment.get("binding_type") == "Half morocco (trade binding)"
        assert result.condition_assessment.get("condition_grade") == "Good"

    def test_parses_market_analysis(self):
        result = parse_analysis_markdown(SAMPLE_MARKDOWN)
        assert result.market_analysis is not None
        assert isinstance(result.market_analysis, dict)
        assert result.market_analysis.get("valuation", {}).get("low") == 40
        assert result.market_analysis.get("valuation", {}).get("mid") == 60
        assert result.market_analysis.get("valuation", {}).get("high") == 80

    def test_parses_recommendations(self):
        result = parse_analysis_markdown(SAMPLE_MARKDOWN)
        assert result.recommendations is not None
        assert "ACQUIRED" in result.recommendations

    def test_empty_markdown_returns_none_fields(self):
        result = parse_analysis_markdown("")
        assert result.executive_summary is None
        assert result.historical_significance is None
        assert result.condition_assessment is None
        assert result.market_analysis is None
        assert result.recommendations is None

    def test_returns_parsed_analysis_dataclass(self):
        result = parse_analysis_markdown(SAMPLE_MARKDOWN)
        assert isinstance(result, ParsedAnalysis)


class TestExtractSections:
    """Test section extraction from markdown."""

    def test_extracts_executive_summary_section(self):
        sections = _extract_sections(SAMPLE_MARKDOWN)
        assert "executive_summary" in sections
        assert "Victorian trade binding" in sections["executive_summary"]

    def test_extracts_historical_significance_section(self):
        sections = _extract_sections(SAMPLE_MARKDOWN)
        assert "historical_significance" in sections

    def test_extracts_condition_assessment_section(self):
        sections = _extract_sections(SAMPLE_MARKDOWN)
        assert "condition_assessment" in sections

    def test_extracts_market_analysis_section(self):
        sections = _extract_sections(SAMPLE_MARKDOWN)
        assert "market_analysis" in sections

    def test_extracts_recommendations_section(self):
        sections = _extract_sections(SAMPLE_MARKDOWN)
        assert "recommendations" in sections

    def test_handles_case_insensitive_headers(self):
        markdown = """## executive summary

This is the summary.

## EXECUTIVE SUMMARY

This is another summary.
"""
        sections = _extract_sections(markdown)
        # Should capture the first one or last one, but not fail
        assert "executive_summary" in sections


class TestParseConditionAssessment:
    """Test condition assessment parsing."""

    def test_extracts_binding_type(self):
        text = "- **Type:** Full leather binding\n- **Grade:** Fine"
        result = _parse_condition_assessment(text)
        assert result["binding_type"] == "Full leather binding"

    def test_extracts_condition_grade(self):
        text = "- **Grade:** Very Good\n- **Notes:** Minor foxing"
        result = _parse_condition_assessment(text)
        assert result["condition_grade"] == "Very Good"

    def test_extracts_condition_notes(self):
        text = "- **Notes:** Spine sunned, corners bumped"
        result = _parse_condition_assessment(text)
        assert result["condition_notes"] == "Spine sunned, corners bumped"

    def test_extracts_spine_description(self):
        text = "- **Spine:** Red morocco with gilt tooling"
        result = _parse_condition_assessment(text)
        assert result["spine"] == "Red morocco with gilt tooling"

    def test_preserves_raw_text(self):
        text = "Some description text"
        result = _parse_condition_assessment(text)
        assert result["raw_text"] == text


class TestParseMarketAnalysis:
    """Test market analysis parsing."""

    def test_extracts_valuation_from_table(self):
        text = """| Metric | Value |
|--------|-------|
| Low | $50 |
| Mid | $100 |
| High | $150 |"""
        result = _parse_market_analysis(text)
        assert result["valuation"]["low"] == 50
        assert result["valuation"]["mid"] == 100
        assert result["valuation"]["high"] == 150

    def test_extracts_purchase_price(self):
        text = "- **Paid:** $85.50"
        result = _parse_market_analysis(text)
        assert result["purchase_price"] == 85.50

    def test_extracts_vs_mid_comparison(self):
        text = "- **vs. Mid:** -15% discount"
        result = _parse_market_analysis(text)
        assert "-15%" in result["vs_mid"]

    def test_handles_comma_in_numbers(self):
        text = "| Low | $1,500 |"
        result = _parse_market_analysis(text)
        assert result["valuation"]["low"] == 1500

    def test_preserves_raw_text(self):
        text = "Market analysis details"
        result = _parse_market_analysis(text)
        assert result["raw_text"] == text


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_minimal_markdown(self):
        markdown = "## Executive Summary\n\nJust a summary."
        result = parse_analysis_markdown(markdown)
        assert result.executive_summary == "Just a summary."
        assert result.condition_assessment is None

    def test_handles_markdown_without_known_sections(self):
        markdown = """## Random Section

Some content here.

## Another Random Section

More content.
"""
        result = parse_analysis_markdown(markdown)
        assert result.executive_summary is None
        assert result.recommendations is None

    def test_handles_markdown_with_only_title(self):
        markdown = "# Book Title\n\nSome intro text."
        result = parse_analysis_markdown(markdown)
        assert result.executive_summary is None

    def test_handles_alternate_section_numbering(self):
        # Test with "## I HISTORICAL" vs "## I. HISTORICAL"
        markdown = """## Executive Summary

Summary here.

## I HISTORICAL & CULTURAL SIGNIFICANCE

History here.
"""
        result = parse_analysis_markdown(markdown)
        assert result.executive_summary == "Summary here."
        assert result.historical_significance == "History here."

    def test_handles_single_hash_headers(self):
        # Test with # instead of ## (alternate format)
        markdown = """# Some Title

# EXECUTIVE SUMMARY

Summary content here.

# I. HISTORICAL & CULTURAL SIGNIFICANCE

History content here.

# II. PHYSICAL DESCRIPTION

- **Type:** Full leather
- **Grade:** Fine

# III. MARKET ANALYSIS

| Metric | Value |
|--------|-------|
| Low | $100 |
| Mid | $150 |
| High | $200 |

# VII. RECOMMENDATIONS

Should acquire.
"""
        result = parse_analysis_markdown(markdown)
        assert result.executive_summary == "Summary content here."
        assert "History content here" in result.historical_significance
        assert result.condition_assessment is not None
        assert result.condition_assessment.get("binding_type") == "Full leather"
        assert result.market_analysis is not None
        assert result.market_analysis.get("valuation", {}).get("mid") == 150
        assert result.recommendations is not None
        assert "acquire" in result.recommendations
