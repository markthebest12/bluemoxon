"""Analysis summary YAML parsing and value calculations.

Extracts structured data from YAML summary block at the top of Napoleon analyses.
"""

import re
from decimal import Decimal
from typing import Any

import yaml


def parse_analysis_summary(analysis_text: str) -> dict[str, Any] | None:
    """Parse YAML summary block from analysis markdown.

    Looks for a YAML block at the start of the analysis, formatted as:
    ## SUMMARY
    ---
    key: value
    ---

    Args:
        analysis_text: Full analysis markdown text

    Returns:
        Dict with parsed values, or None if no summary block found
    """
    if not analysis_text:
        return None

    # Look for YAML block between --- markers after ## SUMMARY
    pattern = r"##\s*SUMMARY\s*\n---\n(.*?)\n---"
    match = re.search(pattern, analysis_text, re.DOTALL | re.IGNORECASE)

    if not match:
        return None

    yaml_content = match.group(1)

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
    """Extract book field updates from parsed YAML summary data.

    Maps YAML fields to book model fields and performs type conversions.

    Args:
        yaml_data: Parsed YAML data dict from parse_analysis_summary()

    Returns:
        Dict of book field names to values, ready to apply to a Book model.
        Only includes fields that have non-null values in the YAML.
    """
    if not yaml_data:
        return {}

    updates: dict[str, Any] = {}

    # Map YAML fields to book model fields
    # estimated_value_low -> value_low
    if yaml_data.get("estimated_value_low") is not None:
        updates["value_low"] = Decimal(str(yaml_data["estimated_value_low"]))

    # estimated_value_high -> value_high
    if yaml_data.get("estimated_value_high") is not None:
        updates["value_high"] = Decimal(str(yaml_data["estimated_value_high"]))

    # Calculate value_mid if both low and high are present
    if "value_low" in updates and "value_high" in updates:
        updates["value_mid"] = (updates["value_low"] + updates["value_high"]) / 2

    # condition_grade (direct mapping)
    if yaml_data.get("condition_grade") is not None:
        updates["condition_grade"] = yaml_data["condition_grade"]

    # acquisition_cost
    if yaml_data.get("acquisition_cost") is not None:
        updates["acquisition_cost"] = Decimal(str(yaml_data["acquisition_cost"]))

    # provenance
    if yaml_data.get("provenance") is not None:
        updates["provenance"] = yaml_data["provenance"]

    # binding_type
    if yaml_data.get("binding_type") is not None:
        updates["binding_type"] = yaml_data["binding_type"]

    # edition
    if yaml_data.get("edition") is not None:
        updates["edition"] = yaml_data["edition"]

    return updates
