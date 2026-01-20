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
