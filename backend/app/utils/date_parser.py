"""Publication date parsing utility.

Parses historical publication date strings into structured year fields.
Handles formats commonly found in antiquarian book records.
"""

import re

from app.enums import Era


def parse_publication_date(date_str: str | None) -> tuple[int | None, int | None]:
    """Parse publication_date string to (year_start, year_end) tuple.

    Handles common historical publication date formats:
    - "1851" -> (1851, 1851)
    - "1867-1880" -> (1867, 1880)
    - "1867-80" -> (1867, 1880)  # Two-digit short form for end year
    - "1880s" -> (1880, 1889)
    - "c.1890" or "circa 1890" -> (1890, 1890)
    - "c.1880-1890" -> (1880, 1890)
    - "[1851]" -> (1851, 1851)  # Uncertain dates in brackets
    - "1851?" -> (1851, 1851)  # Uncertain dates with question mark
    - "n.d." or "no date" -> (None, None)

    Args:
        date_str: Publication date string to parse

    Returns:
        Tuple of (year_start, year_end). Both are None if parsing fails.
        For single years, year_start == year_end.
        For decade format (1880s), returns (1880, 1889).
    """
    # Handle None and empty strings
    if not date_str or not date_str.strip():
        return (None, None)

    # Normalize input: strip whitespace, remove brackets
    cleaned = date_str.strip()

    # Handle "no date" variants first
    if re.match(r"^\[?n\.?d\.?\]?$", cleaned, re.IGNORECASE):
        return (None, None)
    if re.match(r"^no\s+date$", cleaned, re.IGNORECASE):
        return (None, None)

    # Remove square brackets (uncertain dates)
    cleaned = re.sub(r"[\[\]]", "", cleaned)

    # Remove question marks (uncertain dates)
    cleaned = cleaned.replace("?", "")

    # Remove circa prefixes: circa, ca., ca, c. (case insensitive)
    # Order matters: longer patterns first to avoid partial matches
    # The \s* at the end handles optional space between prefix and year
    cleaned = re.sub(r"^(circa\s*|ca\.?\s*|c\.\s*)", "", cleaned, flags=re.IGNORECASE)

    # Strip again after prefix removal
    cleaned = cleaned.strip()

    # Check for decade format: 1880s
    decade_match = re.match(r"^(\d{4})s$", cleaned)
    if decade_match:
        decade_start = int(decade_match.group(1))
        return (decade_start, decade_start + 9)

    # Check for year range: 1867-1880 or 1867 - 1880
    range_match = re.match(r"^(\d{4})\s*-\s*(\d{2,4})$", cleaned)
    if range_match:
        year_start = int(range_match.group(1))
        end_part = range_match.group(2)

        # Handle two-digit short form: 1867-80 -> 1867, 1880
        if len(end_part) == 2:
            # Take century from start year
            century = (year_start // 100) * 100
            year_end = century + int(end_part)
            # Handle century rollover: 1898-02 means 1898-1902
            if year_end < year_start:
                year_end += 100
        else:
            year_end = int(end_part)

        # Normalize reversed ranges
        if year_start > year_end:
            year_start, year_end = year_end, year_start

        return (year_start, year_end)

    # Check for incomplete ranges (invalid)
    if re.match(r"^\d{4}\s*-\s*$", cleaned) or re.match(r"^\s*-\s*\d{4}$", cleaned):
        return (None, None)

    # Check for single year: 1851
    single_match = re.match(r"^(\d{4})$", cleaned)
    if single_match:
        year = int(single_match.group(1))
        return (year, year)

    # No valid format found
    return (None, None)


def compute_era(year_start: int | None, year_end: int | None) -> Era:
    """Compute the historical era from year fields.

    Uses year_start if available, otherwise falls back to year_end.
    Era boundaries are based on British literary/historical periods:
    - Pre-Romantic: Before 1800
    - Romantic: 1800-1836
    - Victorian: 1837-1901
    - Edwardian: 1902-1910
    - Post-1910: After 1910
    - Unknown: No year data available

    Args:
        year_start: Starting year of publication
        year_end: Ending year of publication (for multi-year works)

    Returns:
        Era enum value
    """
    # Use year_start preferentially, fall back to year_end
    year = year_start if year_start is not None else year_end

    if year is None:
        return Era.UNKNOWN

    if year < 1800:
        return Era.PRE_ROMANTIC
    elif year <= 1836:
        return Era.ROMANTIC
    elif year <= 1901:
        return Era.VICTORIAN
    elif year <= 1910:
        return Era.EDWARDIAN
    else:
        return Era.POST_1910
