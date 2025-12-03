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


# Section header patterns to database field mappings
SECTION_MAPPINGS = {
    r"^##\s*Executive\s+Summary\s*$": "executive_summary",
    r"^##\s*I\.?\s*HISTORICAL\s*[&]\s*CULTURAL\s+SIGNIFICANCE\s*$": "historical_significance",
    r"^##\s*II\.?\s*PHYSICAL\s+DESCRIPTION\s*$": "condition_assessment",
    r"^##\s*III\.?\s*MARKET\s+ANALYSIS\s*$": "market_analysis",
    r"^##\s*V\.?\s*RECOMMENDATIONS\s*$": "recommendations",
}


def _extract_sections(markdown: str) -> dict[str, str]:
    """Extract sections from markdown based on ## headers."""
    sections: dict[str, str] = {}
    lines = markdown.split("\n")
    current_section: str | None = None
    current_content: list[str] = []

    for line in lines:
        # Check if this line is a section header
        is_header = False
        for pattern, field_name in SECTION_MAPPINGS.items():
            if re.match(pattern, line.strip(), re.IGNORECASE):
                # Save previous section
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()

                current_section = field_name
                current_content = []
                is_header = True
                break

        # Check for any other ## header (starts a new unmapped section)
        if not is_header and line.strip().startswith("## "):
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = None
            current_content = []
        elif not is_header and current_section:
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


def parse_analysis_markdown(markdown: str) -> ParsedAnalysis:
    """Parse a markdown analysis document into structured fields.

    Args:
        markdown: Raw markdown text of the analysis document.

    Returns:
        ParsedAnalysis with extracted fields populated.
    """
    sections = _extract_sections(markdown)

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
    )
