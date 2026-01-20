"""Tests for validate_lambda_config.py script."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


class TestValidateLambdaConfig:
    """Test suite for Lambda config validation."""

    def test_passes_when_all_required_present(self):
        """Validation passes when all required environment variables are present."""
        from validate_lambda_config import validate_lambda_config, ValidationResult

        expected_vars = {
            "required": [
                {"name": "BMX_DATABASE_URL", "source": "config.py:35"},
                {"name": "BMX_AWS_REGION", "source": "config.py:40"},
            ],
            "optional": [
                {"name": "BMX_DEBUG", "source": "config.py:50"},
            ],
        }

        actual_vars = {
            "BMX_DATABASE_URL": "postgres://...",
            "BMX_AWS_REGION": "us-east-1",
            "BMX_DEBUG": "true",
        }

        result = validate_lambda_config(expected_vars, actual_vars)

        assert isinstance(result, ValidationResult)
        assert result.success is True
        assert result.missing_required == []
        assert result.missing_optional == []

    def test_fails_when_required_missing(self):
        """Validation fails when required environment variables are missing."""
        from validate_lambda_config import validate_lambda_config

        expected_vars = {
            "required": [
                {"name": "BMX_DATABASE_URL", "source": "config.py:35"},
                {"name": "BMX_AWS_REGION", "source": "config.py:40"},
                {"name": "BMX_NEW_FEATURE", "source": "config.py:200"},
            ],
            "optional": [],
        }

        actual_vars = {
            "BMX_DATABASE_URL": "postgres://...",
            # BMX_AWS_REGION is missing
            # BMX_NEW_FEATURE is missing
        }

        result = validate_lambda_config(expected_vars, actual_vars)

        assert result.success is False
        assert len(result.missing_required) == 2

        missing_names = [v["name"] for v in result.missing_required]
        assert "BMX_AWS_REGION" in missing_names
        assert "BMX_NEW_FEATURE" in missing_names

        # Verify source info is preserved
        for var in result.missing_required:
            assert "source" in var

    def test_warns_about_missing_optional(self):
        """Validation passes but reports missing optional vars as warnings."""
        from validate_lambda_config import validate_lambda_config

        expected_vars = {
            "required": [
                {"name": "BMX_DATABASE_URL", "source": "config.py:35"},
            ],
            "optional": [
                {"name": "BMX_DEBUG", "source": "config.py:50"},
                {"name": "BMX_LOG_LEVEL", "source": "config.py:55"},
                {"name": "BMX_CACHE_TTL", "source": "config.py:60"},
            ],
        }

        actual_vars = {
            "BMX_DATABASE_URL": "postgres://...",
            # All optional vars are missing
        }

        result = validate_lambda_config(expected_vars, actual_vars)

        # Should still pass since only optional vars are missing
        assert result.success is True
        assert result.missing_required == []

        # But should report missing optional vars
        assert len(result.missing_optional) == 3

        missing_names = [v["name"] for v in result.missing_optional]
        assert "BMX_DEBUG" in missing_names
        assert "BMX_LOG_LEVEL" in missing_names
        assert "BMX_CACHE_TTL" in missing_names


class TestFormatOutput:
    """Test suite for output formatting functions."""

    def test_format_error_includes_line_numbers(self):
        """Error output includes source file and line numbers."""
        from validate_lambda_config import format_error_output, ValidationResult

        result = ValidationResult(
            success=False,
            missing_required=[
                {"name": "BMX_DATABASE_URL", "source": "config.py:35"},
                {"name": "BMX_NEW_FEATURE", "source": "config.py:200"},
            ],
            missing_optional=[],
        )

        output = format_error_output(result)

        # Should contain the error indicator
        assert "Lambda config validation failed" in output

        # Should list missing vars with source info
        assert "BMX_DATABASE_URL" in output
        assert "config.py:35" in output
        assert "BMX_NEW_FEATURE" in output
        assert "config.py:200" in output

        # Should include Terraform fix hint
        assert "Terraform" in output

    def test_format_success_output(self):
        """Success output includes optional var count."""
        from validate_lambda_config import format_success_output, ValidationResult

        result = ValidationResult(
            success=True,
            missing_required=[],
            missing_optional=[
                {"name": "BMX_DEBUG", "source": "config.py:50"},
                {"name": "BMX_LOG_LEVEL", "source": "config.py:55"},
                {"name": "BMX_CACHE_TTL", "source": "config.py:60"},
            ],
        )

        output = format_success_output(result)

        # Should contain success indicator
        assert "validation passed" in output

        # Should note the optional vars
        assert "3" in output
        assert "optional" in output

    def test_format_success_no_optional_missing(self):
        """Success output when no optional vars are missing."""
        from validate_lambda_config import format_success_output, ValidationResult

        result = ValidationResult(
            success=True,
            missing_required=[],
            missing_optional=[],
        )

        output = format_success_output(result)

        # Should contain success indicator
        assert "validation passed" in output


class TestCLI:
    """Test suite for command-line interface."""

    def test_cli_success_with_json_args(self):
        """CLI returns 0 and success message when validation passes."""
        expected_vars = {
            "required": [
                {"name": "BMX_DATABASE_URL", "source": "config.py:35"},
            ],
            "optional": [],
        }

        actual_vars = {
            "BMX_DATABASE_URL": "postgres://...",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(expected_vars, f)
            expected_file = f.name

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(scripts_dir / "validate_lambda_config.py"),
                    "--expected", expected_file,
                    "--actual", json.dumps(actual_vars),
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            assert "validation passed" in result.stdout
        finally:
            Path(expected_file).unlink()

    def test_cli_failure_exits_with_code_1(self):
        """CLI returns 1 when validation fails."""
        expected_vars = {
            "required": [
                {"name": "BMX_DATABASE_URL", "source": "config.py:35"},
                {"name": "BMX_MISSING_VAR", "source": "config.py:99"},
            ],
            "optional": [],
        }

        actual_vars = {
            "BMX_DATABASE_URL": "postgres://...",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(expected_vars, f)
            expected_file = f.name

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(scripts_dir / "validate_lambda_config.py"),
                    "--expected", expected_file,
                    "--actual", json.dumps(actual_vars),
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 1
            assert "validation failed" in result.stdout
            assert "BMX_MISSING_VAR" in result.stdout
        finally:
            Path(expected_file).unlink()
