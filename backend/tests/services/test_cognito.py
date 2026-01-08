"""Tests for Cognito client service."""

from unittest.mock import MagicMock, patch

import pytest


class TestGetCognitoClient:
    """Tests for get_cognito_client function."""

    def test_returns_cognito_client_when_region_configured(self):
        """Should return a Cognito client when aws_region is set."""
        from app.services.cognito import get_cognito_client

        # Clear cache to ensure fresh call
        get_cognito_client.cache_clear()

        with patch("app.services.cognito.get_settings") as mock_settings:
            mock_settings.return_value.aws_region = "us-east-1"
            with patch("app.services.cognito.boto3") as mock_boto3:
                mock_client = MagicMock()
                mock_boto3.client.return_value = mock_client

                result = get_cognito_client()

                assert result == mock_client
                mock_boto3.client.assert_called_once_with("cognito-idp", region_name="us-east-1")

    def test_raises_value_error_when_region_not_configured(self):
        """Should raise ValueError when aws_region is None."""
        from app.services.cognito import get_cognito_client

        # Clear cache to ensure fresh call
        get_cognito_client.cache_clear()

        with patch("app.services.cognito.get_settings") as mock_settings:
            mock_settings.return_value.aws_region = None

            with pytest.raises(ValueError, match="AWS region not configured"):
                get_cognito_client()

    def test_raises_value_error_when_region_empty_string(self):
        """Should raise ValueError when aws_region is empty string."""
        from app.services.cognito import get_cognito_client

        # Clear cache to ensure fresh call
        get_cognito_client.cache_clear()

        with patch("app.services.cognito.get_settings") as mock_settings:
            mock_settings.return_value.aws_region = ""

            with pytest.raises(ValueError, match="AWS region not configured"):
                get_cognito_client()

    def test_caches_client_instance(self):
        """Should return the same client instance on subsequent calls."""
        from app.services.cognito import get_cognito_client

        # Clear cache to start fresh
        get_cognito_client.cache_clear()

        with patch("app.services.cognito.get_settings") as mock_settings:
            mock_settings.return_value.aws_region = "us-east-1"
            with patch("app.services.cognito.boto3") as mock_boto3:
                mock_client = MagicMock()
                mock_boto3.client.return_value = mock_client

                # Call twice
                result1 = get_cognito_client()
                result2 = get_cognito_client()

                # Should be same instance
                assert result1 is result2
                # boto3.client should only be called once due to caching
                mock_boto3.client.assert_called_once()
