"""Tests for validate_lambda_config.py script."""

import pytest
import sys
from pathlib import Path

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
