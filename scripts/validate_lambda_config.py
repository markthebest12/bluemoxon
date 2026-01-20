#!/usr/bin/env python3
"""
Validate Lambda environment configuration against expected BMX_* variables.

This script compares expected environment variables (from extract_config_vars.py output)
against actual Lambda environment variables to ensure all required vars are set.

Usage:
    python validate_lambda_config.py --expected expected.json --actual '{"VAR": "value"}'
"""

import argparse
import json
import sys
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of validating Lambda config against expected variables."""

    success: bool
    missing_required: list[dict] = field(default_factory=list)
    missing_optional: list[dict] = field(default_factory=list)


def validate_lambda_config(expected_vars: dict, actual_vars: dict) -> ValidationResult:
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
        name = var["name"]
        # Check both existence AND non-empty value for required vars
        if name not in actual_vars or actual_vars[name] == "":
            missing_required.append(var)

    for var in expected_vars.get("optional", []):
        if var["name"] not in actual_vars:
            missing_optional.append(var)

    return ValidationResult(
        success=len(missing_required) == 0,
        missing_required=missing_required,
        missing_optional=missing_optional,
    )


def format_error_output(result: ValidationResult) -> str:
    """
    Format error output for CI when validation fails.

    Args:
        result: ValidationResult with missing required vars.

    Returns:
        Formatted error message string with variable names and source locations.
    """
    lines = []
    lines.append("Lambda config validation failed")
    lines.append("")
    lines.append("Missing required environment variables:")

    for var in result.missing_required:
        name = var["name"]
        source = var.get("source", "unknown")
        lines.append(f"  - {name} (defined in {source})")

    lines.append("")
    lines.append("Fix: Add missing vars to Terraform (infra/terraform/main.tf)")
    lines.append("     then run 'terraform apply' before deploying.")

    return "\n".join(lines)


def format_success_output(result: ValidationResult) -> str:
    """
    Format success output for CI when validation passes.

    Args:
        result: ValidationResult that passed validation.

    Returns:
        Formatted success message string.
    """
    lines = []
    lines.append("Lambda config validation passed")

    if result.missing_optional:
        count = len(result.missing_optional)
        lines.append(f"  Note: {count} optional vars not set")

    return "\n".join(lines)


def main() -> int:
    """
    CLI entry point for Lambda config validation.

    Returns:
        0 on success, 1 on validation failure.
    """
    parser = argparse.ArgumentParser(
        description="Validate Lambda environment configuration against expected BMX_* variables."
    )
    parser.add_argument(
        "--expected",
        required=True,
        help="Path to JSON file with expected vars (from extract_config_vars.py)",
    )
    # Support both --actual (JSON string) and --actual-file (file path)
    # Prefer --actual-file to avoid shell injection with untrusted JSON
    actual_group = parser.add_mutually_exclusive_group(required=True)
    actual_group.add_argument(
        "--actual",
        help="JSON string of actual Lambda env vars (use --actual-file for untrusted input)",
    )
    actual_group.add_argument(
        "--actual-file",
        help="Path to JSON file with actual Lambda env vars (safer than --actual)",
    )

    args = parser.parse_args()

    with open(args.expected) as f:
        expected_vars = json.load(f)

    if args.actual_file:
        with open(args.actual_file) as f:
            actual_vars = json.load(f)
    else:
        actual_vars = json.loads(args.actual)

    result = validate_lambda_config(expected_vars, actual_vars)

    if result.success:
        print(format_success_output(result))  # noqa: T201
        return 0
    else:
        print(format_error_output(result))  # noqa: T201
        return 1


if __name__ == "__main__":
    sys.exit(main())
