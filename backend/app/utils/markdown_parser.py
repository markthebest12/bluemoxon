"""Parse markdown analysis documents into structured fields."""

import re
from dataclasses import dataclass


@dataclass
class ParsedAnalysis:
    """Structured data extracted from an analysis markdown document."""

    executive_summary: str | None = None
    historical_significance: str | None = None
    condition_assessment: dict | None = None
    market_analysis: dict | None = None
    recommendations: str | None = None
    # New v2 fields
    structured_data: dict | None = None
    binder_identification: dict | None = None
    publisher_identification: dict | None = None


# Optional prefix pattern: handles emojis, numbers like "1.", roman numerals like "I."
# Examples: "🎯 ", "1. ", "I. ", "II. ", etc.
_OPT_PREFIX = r"(?:[^\w\s]*\s*)?(?:\d+\.\s*)?(?:[IVX]+\.?\s*)?"

# Section header patterns to database field mappings
# Supports both # and ## header levels for flexibility
# Note: Order matters - more specific patterns should come first
SECTION_MAPPINGS = {
    # Executive Summary variations
    rf"^#{{1,2}}\s*{_OPT_PREFIX}Executive\s+Summary\s*$": "executive_summary",
    rf"^#{{1,2}}\s*{_OPT_PREFIX}ACQUISITION\s+SUMMARY\s*$": "executive_summary",
    rf"^#{{1,2}}\s*{_OPT_PREFIX}Book\s+Description\s*$": "executive_summary",
    rf"^#{{1,2}}\s*{_OPT_PREFIX}Overview\s*$": "executive_summary",
    rf"^#{{1,2}}\s*{_OPT_PREFIX}Summary\s*$": "executive_summary",
    # Historical Significance
    rf"^#{{1,2}}\s*{_OPT_PREFIX}HISTORICAL\s*[&]\s*CULTURAL\s+SIGNIFICANCE\s*$": "historical_significance",
    rf"^#{{1,2}}\s*{_OPT_PREFIX}Historical\s+(?:Context|Significance)\s*$": "historical_significance",
    rf"^#{{1,2}}\s*{_OPT_PREFIX}Binding[/]?Publisher\s+Historical\s+Context\s*$": "historical_significance",
    # Condition Assessment / Physical Description / Binding
    # Napoleon v2 format uses "Detailed Condition Assessment"
    rf"^#{{1,2}}\s*{_OPT_PREFIX}Detailed\s+Condition\s+Assessment\s*$": "condition_assessment",
    rf"^#{{1,2}}\s*{_OPT_PREFIX}PHYSICAL\s+DESCRIPTION\s*$": "condition_assessment",
    rf"^#{{1,2}}\s*{_OPT_PREFIX}BINDING\s*[&]\s*CONDITION\s*$": "condition_assessment",
    rf"^#{{1,2}}\s*{_OPT_PREFIX}Condition\s+Assessment\s*$": "condition_assessment",
    # Market Analysis / Valuation
    # Napoleon v2 format uses "Comprehensive Market Analysis"
    rf"^#{{1,2}}\s*{_OPT_PREFIX}Comprehensive\s+Market\s+Analysis\s*$": "market_analysis",
    rf"^#{{1,2}}\s*{_OPT_PREFIX}MARKET\s+ANALYSIS\s*$": "market_analysis",
    rf"^#{{1,2}}\s*{_OPT_PREFIX}COMPARATIVE\s+MARKET\s+ANALYSIS\s*$": "market_analysis",
    rf"^#{{1,2}}\s*{_OPT_PREFIX}Market\s+(?:Analysis|Positioning)\s*$": "market_analysis",
    rf"^#{{1,2}}\s*{_OPT_PREFIX}Valuation\s*$": "market_analysis",
    # Recommendations / Collection Integration
    # Napoleon v2 format may use "Conclusions and Recommendations"
    rf"^#{{1,2}}\s*{_OPT_PREFIX}Conclusions?\s+and\s+Recommendations?\s*$": "recommendations",
    rf"^#{{1,2}}\s*{_OPT_PREFIX}RECOMMENDATIONS?\s*$": "recommendations",
    rf"^#{{1,2}}\s*{_OPT_PREFIX}Recommendations?\s*$": "recommendations",
    rf"^#{{1,2}}\s*{_OPT_PREFIX}Collection\s+Integration\s*$": "recommendations",
}


def _extract_sections(markdown: str) -> dict[str, str]:
    """Extract sections from markdown based on # or ## headers.

    Tracks header level so that ## subsections are included within # sections.
    A # header ends any current section. A ## header only ends a ## section.
    """
    sections: dict[str, str] = {}
    lines = markdown.split("\n")
    current_section: str | None = None
    current_header_level: int = 0  # 1 for #, 2 for ##
    current_content: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Determine if this is a header and its level
        is_single_hash = stripped.startswith("# ") and not stripped.startswith("## ")
        is_double_hash = stripped.startswith("## ")

        # Check if this line is a mapped section header
        is_mapped_header = False
        for pattern, field_name in SECTION_MAPPINGS.items():
            if re.match(pattern, stripped, re.IGNORECASE):
                # Save previous section
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()

                current_section = field_name
                # Track header level: 1 for single #, 2 for ##
                current_header_level = 1 if is_single_hash else 2
                current_content = []
                is_mapped_header = True
                break

        if is_mapped_header:
            continue

        # Check for unmapped headers that should end the current section
        # A # header always ends the current section
        # A ## header only ends a ## section (not a # section)
        if is_single_hash:
            # Single # always ends any section
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = None
            current_content = []
        elif is_double_hash and current_header_level == 2:
            # Double ## ends a ## section but NOT a # section
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = None
            current_content = []
        elif current_section:
            # Include this line as content (including ## headers within # sections)
            current_content.append(line)

    # Save final section
    if current_section and current_content:
        sections[current_section] = "\n".join(current_content).strip()

    return sections


def _parse_condition_assessment(text: str) -> dict:
    """Parse physical description section into structured condition assessment."""
    result: dict = {"raw_text": text}

    # Extract binding type
    binding_match = re.search(r"\*\*Type:\*\*\s*(.+)", text)
    if binding_match:
        result["binding_type"] = binding_match.group(1).strip()

    # Extract condition grade
    grade_match = re.search(r"\*\*Grade:\*\*\s*(.+)", text)
    if grade_match:
        result["condition_grade"] = grade_match.group(1).strip()

    # Extract condition notes
    notes_match = re.search(r"\*\*Notes:\*\*\s*(.+)", text)
    if notes_match:
        result["condition_notes"] = notes_match.group(1).strip()

    # Extract spine description
    spine_match = re.search(r"\*\*Spine:\*\*\s*(.+)", text)
    if spine_match:
        result["spine"] = spine_match.group(1).strip()

    # Extract bands
    bands_match = re.search(r"\*\*Bands:\*\*\s*(.+)", text)
    if bands_match:
        result["bands"] = bands_match.group(1).strip()

    # Extract boards
    boards_match = re.search(r"\*\*Boards:\*\*\s*(.+)", text)
    if boards_match:
        result["boards"] = boards_match.group(1).strip()

    # Extract style
    style_match = re.search(r"\*\*Style:\*\*\s*(.+)", text)
    if style_match:
        result["style"] = style_match.group(1).strip()

    return result


def _parse_market_analysis(text: str) -> dict:
    """Parse market analysis section into structured data."""
    result: dict = {"raw_text": text}

    # Extract valuation range from table or bold markers
    low_match = re.search(r"Low\s*\|?\s*\$?([\d,]+)", text)
    mid_match = re.search(r"Mid\s*\|?\s*\$?([\d,]+)", text)
    high_match = re.search(r"High\s*\|?\s*\$?([\d,]+)", text)

    if low_match or mid_match or high_match:
        result["valuation"] = {}
        if low_match:
            result["valuation"]["low"] = int(low_match.group(1).replace(",", ""))
        if mid_match:
            result["valuation"]["mid"] = int(mid_match.group(1).replace(",", ""))
        if high_match:
            result["valuation"]["high"] = int(high_match.group(1).replace(",", ""))

    # Extract purchase price
    paid_match = re.search(r"\*\*Paid:\*\*\s*\$?([\d,.]+)", text)
    if paid_match:
        result["purchase_price"] = float(paid_match.group(1).replace(",", ""))

    # Extract vs. mid comparison
    vs_mid_match = re.search(r"\*\*vs\.?\s*Mid:\*\*\s*([+-]?\d+%?\s*\w*)", text)
    if vs_mid_match:
        result["vs_mid"] = vs_mid_match.group(1).strip()

    return result


def strip_structured_data(markdown: str) -> str:
    """Remove the structured data block from markdown for display.

    Strips two formats:
    1. Explicit markers:
       ---STRUCTURED-DATA---
       ...
       ---END-STRUCTURED-DATA---

    2. Metadata Block section header (Napoleon v2 format):
       ## 14. Metadata Block
       ...
       (to end of document)
    """
    # Strip explicit STRUCTURED-DATA markers
    pattern = r"---STRUCTURED-DATA---\s*.*?\s*---END-STRUCTURED-DATA---\s*"
    result = re.sub(pattern, "", markdown, flags=re.DOTALL)

    # Strip "## N. Metadata Block" section and everything after it
    # This is the Napoleon v2 format - uses regex for case-insensitivity
    # and to handle any section number (typically 14, but could vary)
    metadata_pattern = r"\n*## \d+\.\s*Metadata Block.*"
    result = re.sub(metadata_pattern, "", result, flags=re.DOTALL | re.IGNORECASE)

    return result.strip()


def _parse_structured_data(markdown: str) -> dict | None:
    """Extract structured data section from v2 format analysis.

    Looks for:
    ```
    ---STRUCTURED-DATA---
    KEY: value
    ---END-STRUCTURED-DATA---
    ```
    """
    pattern = r"---STRUCTURED-DATA---\s*(.*?)\s*---END-STRUCTURED-DATA---"
    match = re.search(pattern, markdown, re.DOTALL)

    if not match:
        return None

    result: dict = {}
    content = match.group(1).strip()

    for line in content.split("\n"):
        line = line.strip()
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower().replace("-", "_")
            value = value.strip()

            # Convert numeric values
            if key in ("valuation_low", "valuation_mid", "valuation_high", "publication_year"):
                try:
                    result[key] = int(value) if value != "UNKNOWN" else None
                except ValueError:
                    result[key] = None
            else:
                result[key] = value if value != "UNKNOWN" else None

    return result if result else None


def _parse_binder_identification(text: str) -> dict | None:
    """Extract binder identification from binding context section.

    Looks for:
    **Binder Identification:**
    - **Name:** [Binder name]
    - **Confidence:** [HIGH/MEDIUM/LOW]
    - **Evidence:** [What was found]
    """
    result: dict = {}

    # Look for explicit binder identification block
    name_match = re.search(r"\*\*Name:\*\*\s*(.+)", text)
    if name_match:
        name = name_match.group(1).strip()
        if name.lower() not in ("unidentified", "unknown", "none"):
            result["name"] = name

    confidence_match = re.search(r"\*\*Confidence:\*\*\s*(\w+)", text)
    if confidence_match:
        result["confidence"] = confidence_match.group(1).strip().upper()

    evidence_match = re.search(r"\*\*Evidence:\*\*\s*(.+)", text)
    if evidence_match:
        result["evidence"] = evidence_match.group(1).strip()

    auth_match = re.search(r"\*\*Authentication Notes:\*\*\s*(.+)", text)
    if auth_match:
        result["authentication_notes"] = auth_match.group(1).strip()

    # Also check for binder mentions in the text using known binder names
    known_binders = [
        "Sangorski & Sutcliffe",
        "Sangorski",
        "Rivière & Son",
        "Rivière",
        "Riviere",
        "Zaehnsdorf",
        "Cobden-Sanderson",
        "Doves Bindery",
        "Bedford",
        "Morrell",
        "Root & Son",
        "Root",
        "Bayntun",
        "Tout",
        "Stikeman",
    ]

    if "name" not in result:
        # Try to find binder name mentioned with EXPLICIT signature/stamp evidence.
        # Issue #502: Only match patterns that indicate physical signature/stamp,
        # NOT style descriptions like "bound by X" or "X binding".
        # Per Napoleon Framework v3 prompt: Only identify binders with confirmed
        # visible signatures or stamps.
        for binder in known_binders:
            # Patterns requiring explicit physical evidence (signature/stamp)
            patterns = [
                # "X signature visible on turn-in" or "X signature on front turn-in"
                rf"{re.escape(binder)}\s+signature\s+(?:visible\s+)?(?:on|in)",
                # "signature of X" or "signed X visible"
                rf"signature\s+(?:of\s+)?{re.escape(binder)}",
                # "X stamped in gilt" or "X stamp visible"
                rf"{re.escape(binder)}\s+stamp(?:ed)?\s+(?:in\s+gilt|visible|on)",
                # "stamp of X" or "X's stamp"
                rf"stamp\s+(?:of\s+)?{re.escape(binder)}",
                # "signed by X on turn-in" (requires location context)
                rf"signed\s+(?:by\s+)?{re.escape(binder)}\s+(?:on|in)",
            ]
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    result["name"] = binder
                    if "confidence" not in result:
                        result["confidence"] = "HIGH"  # Physical evidence = HIGH confidence
                    break
            if "name" in result:
                break

    return result if result else None


def _parse_publisher_identification(text: str) -> dict | None:
    """Extract publisher identification from markdown text.

    Looks for **Publisher:** pattern in text.
    Structured data parsing is handled separately.
    """
    result: dict = {}

    # Look for **Publisher:** pattern
    publisher_match = re.search(r"\*\*Publisher:\*\*\s*(.+)", text)
    if publisher_match:
        name = publisher_match.group(1).strip()
        if name.lower() not in ("unknown", "unidentified", "none", "n/a"):
            result["name"] = name

    return result if result else None


def parse_analysis_markdown(markdown: str) -> ParsedAnalysis:
    """Parse a markdown analysis document into structured fields.

    Args:
        markdown: Raw markdown text of the analysis document.

    Returns:
        ParsedAnalysis with extracted fields populated.
    """
    sections = _extract_sections(markdown)

    # Extract structured data from v2 format (if present)
    structured_data = _parse_structured_data(markdown)

    # Extract binder identification from full text
    binder_identification = _parse_binder_identification(markdown)

    # If structured data has binder info, merge it
    if structured_data and structured_data.get("binder_identified"):
        if not binder_identification:
            binder_identification = {}
        if "name" not in binder_identification:
            binder_identification["name"] = structured_data["binder_identified"]
        if "confidence" not in binder_identification and structured_data.get("binder_confidence"):
            binder_identification["confidence"] = structured_data["binder_confidence"]

    # Extract publisher identification from text patterns
    publisher_identification = _parse_publisher_identification(markdown)

    # If structured data has publisher info, it takes precedence
    if structured_data and structured_data.get("publisher_identified"):
        publisher_identification = {
            "name": structured_data["publisher_identified"],
        }
        if structured_data.get("publisher_confidence"):
            publisher_identification["confidence"] = structured_data["publisher_confidence"]

    return ParsedAnalysis(
        executive_summary=sections.get("executive_summary"),
        historical_significance=sections.get("historical_significance"),
        condition_assessment=(
            _parse_condition_assessment(sections["condition_assessment"])
            if "condition_assessment" in sections
            else None
        ),
        market_analysis=(
            _parse_market_analysis(sections["market_analysis"])
            if "market_analysis" in sections
            else None
        ),
        recommendations=sections.get("recommendations"),
        structured_data=structured_data,
        binder_identification=binder_identification,
        publisher_identification=publisher_identification,
    )
