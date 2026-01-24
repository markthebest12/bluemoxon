"""Analysis summary parsing and value calculations.

Extracts structured data from Napoleon v2 analysis format.
Supports both the new STRUCTURED-DATA format and legacy YAML format.
"""

import logging
import re
from decimal import Decimal
from typing import Any

import yaml

from app.enums import ConditionGrade

logger = logging.getLogger(__name__)

# Mapping of common AI aliases to valid ConditionGrade enum values
CONDITION_GRADE_ALIASES: dict[str, str] = {
    # Exact enum values (uppercase)
    "FINE": ConditionGrade.FINE.value,
    "NEAR_FINE": ConditionGrade.NEAR_FINE.value,
    "VERY_GOOD": ConditionGrade.VERY_GOOD.value,
    "GOOD": ConditionGrade.GOOD.value,
    "FAIR": ConditionGrade.FAIR.value,
    "POOR": ConditionGrade.POOR.value,
    # Common abbreviations
    "VG": ConditionGrade.VERY_GOOD.value,
    "VG+": ConditionGrade.NEAR_FINE.value,
    "VG-": ConditionGrade.VERY_GOOD.value,
    "NF": ConditionGrade.NEAR_FINE.value,
    "G": ConditionGrade.GOOD.value,
    "G+": ConditionGrade.GOOD.value,
    "F": ConditionGrade.FINE.value,
    # Human-readable variants (with spaces)
    "NEAR FINE": ConditionGrade.NEAR_FINE.value,
    "VERY GOOD": ConditionGrade.VERY_GOOD.value,
}


def normalize_condition_grade(value: str | None) -> str | None:
    """Normalize AI-generated condition grade to valid enum value.

    Handles common aliases and case variations from AI analysis output.

    Args:
        value: Raw condition grade string from AI output

    Returns:
        Valid ConditionGrade enum value, or None if invalid/unrecognized
    """
    if value is None:
        return None

    if not isinstance(value, str):
        return None

    # Strip whitespace and normalize
    normalized = value.strip().upper().replace("_", " ").replace("-", " ")

    # Also try with underscores for enum-style values
    with_underscores = normalized.replace(" ", "_")

    # Check aliases (case-insensitive via uppercase normalization)
    if normalized in CONDITION_GRADE_ALIASES:
        return CONDITION_GRADE_ALIASES[normalized]

    if with_underscores in CONDITION_GRADE_ALIASES:
        return CONDITION_GRADE_ALIASES[with_underscores]

    # Try direct enum lookup
    try:
        return ConditionGrade(with_underscores).value
    except ValueError:
        pass

    logger.warning(f"Unrecognized condition grade: {value!r}, skipping")
    return None


def parse_analysis_summary(analysis_text: str) -> dict[str, Any] | None:
    """Parse structured data block from Napoleon analysis.

    Supports two formats:
    1. Napoleon v2 format (preferred):
       ---STRUCTURED-DATA---
       CONDITION_GRADE: VG+
       VALUATION_LOW: 200
       ---END-STRUCTURED-DATA---

    2. Legacy YAML format:
       ## SUMMARY
       ---
       key: value
       ---

    Args:
        analysis_text: Full analysis markdown text

    Returns:
        Dict with parsed values (normalized to lowercase keys), or None if no block found
    """
    if not analysis_text:
        return None

    # Try Napoleon v2 format first (---STRUCTURED-DATA---)
    v2_pattern = r"---STRUCTURED-DATA---\s*\n(.*?)\n---END-STRUCTURED-DATA---"
    match = re.search(v2_pattern, analysis_text, re.DOTALL | re.IGNORECASE)

    if match:
        return _parse_structured_data_block(match.group(1))

    # Fall back to legacy YAML format (## SUMMARY)
    legacy_pattern = r"##\s*SUMMARY\s*\n---\n(.*?)\n---"
    match = re.search(legacy_pattern, analysis_text, re.DOTALL | re.IGNORECASE)

    if match:
        return _parse_yaml_block(match.group(1))

    return None


def _parse_structured_data_block(content: str) -> dict[str, Any] | None:
    """Parse Napoleon v2 STRUCTURED-DATA block.

    Format: KEY: value (one per line)
    Keys are normalized to lowercase with underscores.
    """
    data = {}

    for line in content.strip().split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue

        # Split on first colon only
        key, value = line.split(":", 1)
        key = key.strip().lower().replace(" ", "_")
        value = value.strip()

        # Skip placeholder values
        if value in ("[", "]", "UNKNOWN", ""):
            continue

        # Try to convert numeric values
        if key in ("valuation_low", "valuation_mid", "valuation_high", "publication_year"):
            try:
                # Remove $ and commas from price values
                clean_value = value.replace("$", "").replace(",", "")
                data[key] = int(float(clean_value))
            except (ValueError, TypeError):
                data[key] = value
        else:
            data[key] = value

    logger.info(f"Parsed structured data block: {list(data.keys())}")
    return data if data else None


def _parse_yaml_block(yaml_content: str) -> dict[str, Any] | None:
    """Parse legacy YAML summary block."""
    try:
        data = yaml.safe_load(yaml_content)
        if not isinstance(data, dict):
            return None
        return data
    except yaml.YAMLError:
        return None


def calculate_value_vs_cost(
    acquisition_cost: float | None,
    estimated_value_low: float | int | None,
    estimated_value_high: float | int | None,
) -> str | None:
    """Calculate the value vs cost percentage.

    Args:
        acquisition_cost: What was paid for the book
        estimated_value_low: Low end of FMV estimate
        estimated_value_high: High end of FMV estimate

    Returns:
        String like "50% below FMV", "25% above FMV", or "At FMV"
        Returns None if any required value is missing
    """
    if acquisition_cost is None:
        return None
    if estimated_value_low is None or estimated_value_high is None:
        return None

    # Calculate midpoint of FMV range
    fmv_midpoint = (estimated_value_low + estimated_value_high) / 2

    if fmv_midpoint == 0:
        return None

    # Calculate percentage difference
    diff = fmv_midpoint - acquisition_cost
    percentage = abs(diff / fmv_midpoint) * 100

    # Round to nearest integer
    percentage = round(percentage)

    if percentage < 1:
        return "At FMV"
    elif diff > 0:
        return f"{percentage}% below FMV"
    else:
        return f"{percentage}% above FMV"


def extract_book_updates_from_yaml(yaml_data: dict[str, Any] | None) -> dict[str, Any]:
    """Extract book field updates from parsed structured data.

    Maps Napoleon v2 and legacy YAML fields to book model fields.

    Supported field mappings:
    - Napoleon v2: valuation_low, valuation_mid, valuation_high, condition_grade, binding_type
    - Legacy: estimated_value_low, estimated_value_high, condition_grade, etc.

    Args:
        yaml_data: Parsed data dict from parse_analysis_summary()

    Returns:
        Dict of book field names to values, ready to apply to a Book model.
        Only includes fields that have non-null values.
    """
    if not yaml_data:
        return {}

    updates: dict[str, Any] = {}

    # Value fields - support both Napoleon v2 (valuation_*) and legacy (estimated_value_*) names
    value_low = yaml_data.get("valuation_low") or yaml_data.get("estimated_value_low")
    value_mid = yaml_data.get("valuation_mid") or yaml_data.get("estimated_value_mid")
    value_high = yaml_data.get("valuation_high") or yaml_data.get("estimated_value_high")

    if value_low is not None:
        updates["value_low"] = Decimal(str(value_low))

    if value_high is not None:
        updates["value_high"] = Decimal(str(value_high))

    # Use provided mid value, or calculate if both low and high are present
    if value_mid is not None:
        updates["value_mid"] = Decimal(str(value_mid))
    elif "value_low" in updates and "value_high" in updates:
        updates["value_mid"] = (updates["value_low"] + updates["value_high"]) / 2

    # condition_grade - validate and normalize to enum value
    raw_condition = yaml_data.get("condition_grade")
    if raw_condition is not None:
        normalized = normalize_condition_grade(raw_condition)
        if normalized is not None:
            updates["condition_grade"] = normalized

    # acquisition_cost
    if yaml_data.get("acquisition_cost") is not None:
        updates["acquisition_cost"] = Decimal(str(yaml_data["acquisition_cost"]))

    # provenance
    if yaml_data.get("provenance") is not None:
        updates["provenance"] = yaml_data["provenance"]

    # binding_type (same name in both formats)
    if yaml_data.get("binding_type") is not None:
        updates["binding_type"] = yaml_data["binding_type"]

    # edition
    if yaml_data.get("edition") is not None:
        updates["edition"] = yaml_data["edition"]

    if updates:
        logger.info(f"Extracted book updates: {list(updates.keys())}")

    return updates
