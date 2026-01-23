"""Tests for centralized AWS client factories."""

from unittest.mock import MagicMock, patch

import pytest


class TestGetS3Client:
    """Tests for get_s3_client function."""

    def test_returns_s3_client_with_region(self):
        """Should return an S3 client with region configured."""
        from app.services.aws_clients import get_s3_client

        get_s3_client.cache_clear()

        with patch("app.services.aws_clients.get_settings") as mock_settings:
            mock_settings.return_value.aws_region = "us-west-2"
            with patch.dict("os.environ", {}, clear=True):
                with patch("app.services.aws_clients.boto3") as mock_boto3:
                    mock_client = MagicMock()
                    mock_boto3.client.return_value = mock_client

                    result = get_s3_client()

                    assert result == mock_client
                    mock_boto3.client.assert_called_once_with(
                        "s3", region_name="us-west-2"
                    )

    def test_prefers_aws_region_env_var(self):
        """Should prefer AWS_REGION env var over settings."""
        from app.services.aws_clients import get_s3_client

        get_s3_client.cache_clear()

        with patch("app.services.aws_clients.get_settings") as mock_settings:
            mock_settings.return_value.aws_region = "us-west-2"
            with patch.dict("os.environ", {"AWS_REGION": "us-east-1"}):
                with patch("app.services.aws_clients.boto3") as mock_boto3:
                    mock_client = MagicMock()
                    mock_boto3.client.return_value = mock_client

                    result = get_s3_client()

                    mock_boto3.client.assert_called_once_with(
                        "s3", region_name="us-east-1"
                    )

    def test_caches_client_instance(self):
        """Should return the same client instance on subsequent calls."""
        from app.services.aws_clients import get_s3_client

        get_s3_client.cache_clear()

        with patch("app.services.aws_clients.get_settings") as mock_settings:
            mock_settings.return_value.aws_region = "us-west-2"
            with patch("app.services.aws_clients.boto3") as mock_boto3:
                mock_client = MagicMock()
                mock_boto3.client.return_value = mock_client

                result1 = get_s3_client()
                result2 = get_s3_client()

                assert result1 is result2
                mock_boto3.client.assert_called_once()


class TestGetSqsClient:
    """Tests for get_sqs_client function."""

    def test_returns_sqs_client_with_region(self):
        """Should return an SQS client with region configured."""
        from app.services.aws_clients import get_sqs_client

        get_sqs_client.cache_clear()

        with patch("app.services.aws_clients.get_settings") as mock_settings:
            mock_settings.return_value.aws_region = "us-west-2"
            with patch.dict("os.environ", {}, clear=True):
                with patch("app.services.aws_clients.boto3") as mock_boto3:
                    mock_client = MagicMock()
                    mock_boto3.client.return_value = mock_client

                    result = get_sqs_client()

                    assert result == mock_client
                    mock_boto3.client.assert_called_once_with(
                        "sqs", region_name="us-west-2"
                    )

    def test_prefers_aws_region_env_var(self):
        """Should prefer AWS_REGION env var over settings."""
        from app.services.aws_clients import get_sqs_client

        get_sqs_client.cache_clear()

        with patch("app.services.aws_clients.get_settings") as mock_settings:
            mock_settings.return_value.aws_region = "us-west-2"
            with patch.dict("os.environ", {"AWS_REGION": "us-east-1"}):
                with patch("app.services.aws_clients.boto3") as mock_boto3:
                    mock_client = MagicMock()
                    mock_boto3.client.return_value = mock_client

                    result = get_sqs_client()

                    mock_boto3.client.assert_called_once_with(
                        "sqs", region_name="us-east-1"
                    )

    def test_caches_client_instance(self):
        """Should return the same client instance on subsequent calls."""
        from app.services.aws_clients import get_sqs_client

        get_sqs_client.cache_clear()

        with patch("app.services.aws_clients.get_settings") as mock_settings:
            mock_settings.return_value.aws_region = "us-west-2"
            with patch("app.services.aws_clients.boto3") as mock_boto3:
                mock_client = MagicMock()
                mock_boto3.client.return_value = mock_client

                result1 = get_sqs_client()
                result2 = get_sqs_client()

                assert result1 is result2
                mock_boto3.client.assert_called_once()


class TestGetLambdaClient:
    """Tests for get_lambda_client function."""

    def test_returns_lambda_client_with_region(self):
        """Should return a Lambda client with region configured."""
        from app.services.aws_clients import get_lambda_client

        get_lambda_client.cache_clear()

        with patch("app.services.aws_clients.get_settings") as mock_settings:
            mock_settings.return_value.aws_region = "us-west-2"
            with patch.dict("os.environ", {}, clear=True):
                with patch("app.services.aws_clients.boto3") as mock_boto3:
                    mock_client = MagicMock()
                    mock_boto3.client.return_value = mock_client

                    result = get_lambda_client()

                    assert result == mock_client
                    mock_boto3.client.assert_called_once_with(
                        "lambda", region_name="us-west-2"
                    )

    def test_prefers_aws_region_env_var(self):
        """Should prefer AWS_REGION env var over settings."""
        from app.services.aws_clients import get_lambda_client

        get_lambda_client.cache_clear()

        with patch("app.services.aws_clients.get_settings") as mock_settings:
            mock_settings.return_value.aws_region = "us-west-2"
            with patch.dict("os.environ", {"AWS_REGION": "us-east-1"}):
                with patch("app.services.aws_clients.boto3") as mock_boto3:
                    mock_client = MagicMock()
                    mock_boto3.client.return_value = mock_client

                    result = get_lambda_client()

                    mock_boto3.client.assert_called_once_with(
                        "lambda", region_name="us-east-1"
                    )

    def test_caches_client_instance(self):
        """Should return the same client instance on subsequent calls."""
        from app.services.aws_clients import get_lambda_client

        get_lambda_client.cache_clear()

        with patch("app.services.aws_clients.get_settings") as mock_settings:
            mock_settings.return_value.aws_region = "us-west-2"
            with patch("app.services.aws_clients.boto3") as mock_boto3:
                mock_client = MagicMock()
                mock_boto3.client.return_value = mock_client

                result1 = get_lambda_client()
                result2 = get_lambda_client()

                assert result1 is result2
                mock_boto3.client.assert_called_once()
