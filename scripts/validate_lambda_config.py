#!/usr/bin/env python3
"""
Validate Lambda environment configuration against expected BMX_* variables.

This script compares expected environment variables (from extract_config_vars.py output)
against actual Lambda environment variables to ensure all required vars are set.
"""

from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of validating Lambda config against expected variables."""

    success: bool
    missing_required: list[dict] = field(default_factory=list)
    missing_optional: list[dict] = field(default_factory=list)


def validate_lambda_config(
    expected_vars: dict, actual_vars: dict
) -> ValidationResult:
    """
    Validate that actual Lambda env vars contain all expected required vars.

    Args:
        expected_vars: Dict with 'required' and 'optional' lists of var definitions.
                       Each var is a dict with 'name' and 'source' keys.
        actual_vars: Dict of actual environment variable names to values.

    Returns:
        ValidationResult with success status and lists of missing vars.
    """
    missing_required = []
    missing_optional = []

    for var in expected_vars.get("required", []):
        if var["name"] not in actual_vars:
            missing_required.append(var)

    for var in expected_vars.get("optional", []):
        if var["name"] not in actual_vars:
            missing_optional.append(var)

    return ValidationResult(
        success=len(missing_required) == 0,
        missing_required=missing_required,
        missing_optional=missing_optional,
    )
