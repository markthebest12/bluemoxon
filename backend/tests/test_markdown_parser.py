"""Tests for markdown analysis parser."""

from app.utils.markdown_parser import (
    ParsedAnalysis,
    _extract_sections,
    _parse_binder_identification,
    _parse_condition_assessment,
    _parse_market_analysis,
    _parse_structured_data,
    parse_analysis_markdown,
    strip_structured_data,
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


class TestParseStructuredData:
    """Test v2 structured data parsing."""

    def test_extracts_full_structured_data(self):
        markdown = """---STRUCTURED-DATA---
CONDITION_GRADE: VG+
BINDER_IDENTIFIED: Zaehnsdorf
BINDER_CONFIDENCE: HIGH
BINDING_TYPE: Full Morocco
VALUATION_LOW: 500
VALUATION_MID: 750
VALUATION_HIGH: 1000
ERA_PERIOD: Victorian
PUBLICATION_YEAR: 1885
---END-STRUCTURED-DATA---

## Executive Summary
Some content here.
"""
        result = _parse_structured_data(markdown)
        assert result is not None
        assert result["condition_grade"] == "VG+"
        assert result["binder_identified"] == "Zaehnsdorf"
        assert result["binder_confidence"] == "HIGH"
        assert result["binding_type"] == "Full Morocco"
        assert result["valuation_low"] == 500
        assert result["valuation_mid"] == 750
        assert result["valuation_high"] == 1000
        assert result["era_period"] == "Victorian"
        assert result["publication_year"] == 1885

    def test_handles_unknown_values(self):
        markdown = """---STRUCTURED-DATA---
CONDITION_GRADE: Good
BINDER_IDENTIFIED: UNKNOWN
PUBLICATION_YEAR: UNKNOWN
---END-STRUCTURED-DATA---
"""
        result = _parse_structured_data(markdown)
        assert result is not None
        assert result["condition_grade"] == "Good"
        assert result["binder_identified"] is None
        assert result["publication_year"] is None

    def test_returns_none_without_structured_data(self):
        markdown = """## Executive Summary
Just a regular analysis without structured data.
"""
        result = _parse_structured_data(markdown)
        assert result is None

    def test_handles_malformed_structured_data(self):
        # Note: lines with colons still get parsed, even if not valid keys
        # This tests a line WITHOUT a colon
        markdown = """---STRUCTURED-DATA---
This line has no colon so cannot be parsed
---END-STRUCTURED-DATA---
"""
        result = _parse_structured_data(markdown)
        # Should return None since no valid keys found
        assert result is None


class TestParseBinderIdentification:
    """Test binder identification parsing."""

    def test_extracts_explicit_binder_block(self):
        text = """**Binder Identification:**
- **Name:** Sangorski & Sutcliffe
- **Confidence:** HIGH
- **Evidence:** Signed in gilt on front turn-in
- **Authentication Notes:** Check endpapers for additional stamps
"""
        result = _parse_binder_identification(text)
        assert result is not None
        assert result["name"] == "Sangorski & Sutcliffe"
        assert result["confidence"] == "HIGH"
        assert "Signed in gilt" in result["evidence"]
        assert "endpapers" in result["authentication_notes"]

    def test_extracts_signed_binder(self):
        """Explicit signature mention SHOULD identify binder."""
        text = "Signed by Bayntun on the front turn-in."
        result = _parse_binder_identification(text)
        assert result is not None
        assert result["name"] == "Bayntun"

    def test_extracts_stamped_binder(self):
        """Explicit stamp mention SHOULD identify binder."""
        text = "Zaehnsdorf stamped in gilt on turn-in."
        result = _parse_binder_identification(text)
        assert result is not None
        assert result["name"] == "Zaehnsdorf"

    def test_returns_none_for_no_binder(self):
        text = "A standard publisher's cloth binding in good condition."
        result = _parse_binder_identification(text)
        assert result is None

    def test_ignores_unidentified_name(self):
        text = """**Binder Identification:**
- **Name:** Unidentified
- **Confidence:** NONE
"""
        result = _parse_binder_identification(text)
        assert result is None or "name" not in result

    def test_handles_unknown_name(self):
        text = """**Binder Identification:**
- **Name:** Unknown
"""
        result = _parse_binder_identification(text)
        assert result is None or "name" not in result

    # Issue #502: Tests for correct binder detection behavior
    # These tests enforce that style mentions do NOT trigger binder identification
    # Only explicit signature/stamp evidence should identify a binder

    def test_style_mention_does_not_identify_binder(self):
        """Style mentions like 'Rivière-style' should NOT identify binder.

        Issue #502: The AI correctly says BINDER_IDENTIFIED: UNKNOWN for style
        mentions, but fallback patterns were overriding this. Style observations
        belong in binding description, NOT in binder identification.
        """
        text = "A fine Rivière-style binding with exceptional gilt work."
        result = _parse_binder_identification(text)
        # Should NOT identify a binder from style mention alone
        assert result is None or "name" not in result

    def test_bound_by_without_signature_does_not_identify_binder(self):
        """'Bound by' without signature evidence should NOT identify binder.

        Issue #502: 'bound by Zaehnsdorf' could mean style description,
        not attribution with signature evidence.
        """
        text = "This volume was bound by Zaehnsdorf in their characteristic style."
        result = _parse_binder_identification(text)
        # Should NOT identify without signature evidence
        assert result is None or "name" not in result

    def test_binding_type_mention_does_not_identify_binder(self):
        """'Rivière binding' style description should NOT identify binder.

        Issue #502: 'A fine Rivière binding' describes the style, not
        confirmed attribution with signature.
        """
        text = "A fine Rivière binding with exceptional gilt work."
        result = _parse_binder_identification(text)
        # Should NOT identify from style description
        assert result is None or "name" not in result

    def test_structured_unknown_not_overridden_by_text_mention(self):
        """When structured data says UNKNOWN, text patterns should NOT override.

        Issue #502: AI correctly identifies BINDER_IDENTIFIED: UNKNOWN, but
        if text mentions 'Rivière-style', fallback should NOT set binder.
        """
        text = """---STRUCTURED-DATA---
BINDER_IDENTIFIED: UNKNOWN
BINDER_CONFIDENCE: NONE
---END-STRUCTURED-DATA---

The binding exhibits Rivière-style tooling and design elements,
suggesting influence from that workshop tradition.
"""
        # When parsing the full markdown, binder should stay UNKNOWN
        from app.utils.markdown_parser import parse_analysis_markdown

        result = parse_analysis_markdown(text)
        # Binder identification should be None (UNKNOWN in structured data)
        assert result.binder_identification is None or "name" not in result.binder_identification

    def test_signature_on_turn_in_identifies_binder(self):
        """Explicit signature statement SHOULD identify binder.

        This is the CORRECT case - signature evidence justifies identification.
        """
        text = "Rivière & Son signature visible on front turn-in."
        result = _parse_binder_identification(text)
        assert result is not None
        assert "Rivière" in result.get("name", "")


class TestStripStructuredData:
    """Test strip_structured_data function."""

    def test_strips_structured_data_block(self):
        markdown = """---STRUCTURED-DATA---
CONDITION_GRADE: VG+
BINDER_IDENTIFIED: Zaehnsdorf
---END-STRUCTURED-DATA---

## Executive Summary

A fine binding in excellent condition.
"""
        result = strip_structured_data(markdown)
        assert "---STRUCTURED-DATA---" not in result
        assert "---END-STRUCTURED-DATA---" not in result
        assert "CONDITION_GRADE" not in result
        assert "## Executive Summary" in result
        assert "A fine binding" in result

    def test_preserves_content_without_structured_data(self):
        markdown = """## Executive Summary

A fine binding in excellent condition.
"""
        result = strip_structured_data(markdown)
        assert "## Executive Summary" in result
        assert "A fine binding" in result

    def test_handles_empty_string(self):
        result = strip_structured_data("")
        assert result == ""


class TestPublisherIdentification:
    """Test publisher identification extraction from markdown."""

    def test_extracts_publisher_from_structured_data(self):
        """Extract publisher from STRUCTURED-DATA block."""
        markdown = """---STRUCTURED-DATA---
PUBLISHER_IDENTIFIED: Harper & Brothers
PUBLISHER_CONFIDENCE: HIGH
---END-STRUCTURED-DATA---

## Executive Summary
A fine first edition.
"""
        result = parse_analysis_markdown(markdown)
        assert result.publisher_identification is not None
        assert result.publisher_identification["name"] == "Harper & Brothers"
        assert result.publisher_identification["confidence"] == "HIGH"

    def test_extracts_publisher_from_text_pattern(self):
        """Extract publisher from **Publisher:** pattern in text."""
        markdown = """## Executive Summary

A fine Victorian binding.

## II. PHYSICAL DESCRIPTION

**Publisher:** Macmillan and Co., London
**Binding:** Full Morocco
"""
        result = parse_analysis_markdown(markdown)
        assert result.publisher_identification is not None
        assert result.publisher_identification["name"] == "Macmillan and Co., London"

    def test_structured_data_publisher_takes_precedence(self):
        """Structured data should take precedence over text patterns."""
        markdown = """---STRUCTURED-DATA---
PUBLISHER_IDENTIFIED: Oxford University Press
PUBLISHER_CONFIDENCE: HIGH
---END-STRUCTURED-DATA---

## II. PHYSICAL DESCRIPTION

**Publisher:** Some Other Publisher
"""
        result = parse_analysis_markdown(markdown)
        assert result.publisher_identification is not None
        assert result.publisher_identification["name"] == "Oxford University Press"

    def test_handles_unknown_publisher(self):
        """UNKNOWN publisher should result in None."""
        markdown = """---STRUCTURED-DATA---
PUBLISHER_IDENTIFIED: UNKNOWN
PUBLISHER_CONFIDENCE: LOW
---END-STRUCTURED-DATA---
"""
        result = parse_analysis_markdown(markdown)
        assert result.publisher_identification is None or "name" not in result.publisher_identification

    def test_extracts_publisher_with_location(self):
        """Should extract publisher even with location suffix."""
        markdown = """## II. PHYSICAL DESCRIPTION

**Publisher:** Chapman & Hall, London
**Year:** 1859
"""
        result = parse_analysis_markdown(markdown)
        assert result.publisher_identification is not None
        assert "Chapman & Hall" in result.publisher_identification["name"]

    def test_no_publisher_returns_none(self):
        """When no publisher info present, should return None."""
        markdown = """## Executive Summary

A fine binding with no publisher information.
"""
        result = parse_analysis_markdown(markdown)
        assert result.publisher_identification is None


class TestV2Integration:
    """Test v2 features integration in main parser."""

    def test_parses_v2_format_with_structured_data(self):
        markdown = """---STRUCTURED-DATA---
CONDITION_GRADE: Fine
BINDER_IDENTIFIED: Rivière & Son
BINDER_CONFIDENCE: HIGH
VALUATION_LOW: 800
VALUATION_MID: 1200
VALUATION_HIGH: 1600
---END-STRUCTURED-DATA---

## Executive Summary

A magnificent Rivière binding in fine condition.

## II. PHYSICAL DESCRIPTION

**Binder Identification:**
- **Name:** Rivière & Son
- **Confidence:** HIGH
- **Evidence:** Signed in gilt on turn-in
"""
        result = parse_analysis_markdown(markdown)
        assert result.structured_data is not None
        assert result.structured_data["condition_grade"] == "Fine"
        assert result.structured_data["valuation_mid"] == 1200

        assert result.binder_identification is not None
        assert result.binder_identification["name"] == "Rivière & Son"
        assert result.binder_identification["confidence"] == "HIGH"

    def test_style_description_does_not_identify_binder(self):
        """Issue #502: 'bound by X' style descriptions should NOT identify binder.

        Only explicit signature/stamp evidence should trigger identification.
        The Napoleon Framework prompt explicitly states: 'Only identify binders
        with confirmed visible signatures or stamps.'
        """
        markdown = """## Executive Summary

This volume was bound by Sangorski & Sutcliffe in their distinctive style.
"""
        result = parse_analysis_markdown(markdown)
        # Style description should NOT identify binder
        assert result.binder_identification is None or "name" not in result.binder_identification

    def test_v1_format_still_works(self):
        # Ensure backward compatibility with v1 format (no structured data)
        result = parse_analysis_markdown(SAMPLE_MARKDOWN)
        assert result.executive_summary is not None
        assert result.condition_assessment is not None
        assert result.market_analysis is not None
        # structured_data should be None for v1 format
        assert result.structured_data is None

    def test_napoleon_v2_detailed_headers(self):
        """Test parsing Napoleon v2 format with 'Detailed' and 'Comprehensive' headers.

        The Napoleon v2 prompt generates headers like:
        - '## 2. Detailed Condition Assessment' (not just 'Condition Assessment')
        - '## 3. Comprehensive Market Analysis' (not just 'Market Analysis')
        """
        markdown = """## 1. Executive Summary

A comprehensive analysis of a Victorian book.

---

## 2. Detailed Condition Assessment

**Type:** Half Morocco
**Grade:** Good+
**Notes:** Moderate wear, structurally sound

### Spine Examination
The spine shows gilt lettering in good condition.

---

## 3. Comprehensive Market Analysis

### Recent Comparable Sales

| Estimate | Value |
|----------|-------|
| Low | $250 |
| Mid | $375 |
| High | $550 |

---

## 5. Binding/Publisher Historical Context

### Publisher History
D. Appleton and Company was founded in 1831.

---

## 12. Conclusions and Recommendations

### Strategic Summary
This set represents a solid mid-range collectible.
"""
        result = parse_analysis_markdown(markdown)

        # Should parse executive summary
        assert result.executive_summary is not None
        assert "comprehensive analysis" in result.executive_summary.lower()

        # Should parse "Detailed Condition Assessment"
        assert result.condition_assessment is not None
        assert result.condition_assessment["binding_type"] == "Half Morocco"
        assert result.condition_assessment["condition_grade"] == "Good+"
        assert "Spine Examination" in result.condition_assessment["raw_text"]

        # Should parse "Comprehensive Market Analysis"
        assert result.market_analysis is not None
        assert result.market_analysis["valuation"]["low"] == 250
        assert result.market_analysis["valuation"]["mid"] == 375
        assert result.market_analysis["valuation"]["high"] == 550

        # Should parse historical context
        assert result.historical_significance is not None
        assert "Appleton" in result.historical_significance

        # Should parse "Conclusions and Recommendations"
        assert result.recommendations is not None
        assert "mid-range collectible" in result.recommendations
