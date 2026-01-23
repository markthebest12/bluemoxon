"""Tests for centralized AWS client factories.

Issue #1241: Boto3 client reuse optimization.
Issue #1262: Consolidated boto3 client factories into aws_clients module.
"""


class TestAwsClientsCaching:
    """Tests for centralized AWS client caching in aws_clients module."""

    def test_get_s3_client_returns_same_instance(self):
        """Verify get_s3_client returns cached instance on repeated calls."""
        from app.services.aws_clients import get_s3_client

        get_s3_client.cache_clear()

        client1 = get_s3_client()
        client2 = get_s3_client()

        assert client1 is client2, (
            "get_s3_client() should return the same cached instance "
            "to reuse TCP connections across requests"
        )

    def test_get_sqs_client_returns_same_instance(self):
        """Verify get_sqs_client returns cached instance on repeated calls."""
        from app.services.aws_clients import get_sqs_client

        get_sqs_client.cache_clear()

        client1 = get_sqs_client()
        client2 = get_sqs_client()

        assert client1 is client2, (
            "get_sqs_client() should return the same cached instance "
            "to reuse TCP connections across requests"
        )

    def test_get_lambda_client_returns_same_instance(self, monkeypatch):
        """Verify get_lambda_client returns cached instance on repeated calls."""
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

        from app.services.aws_clients import get_lambda_client

        get_lambda_client.cache_clear()

        client1 = get_lambda_client()
        client2 = get_lambda_client()

        assert client1 is client2, (
            "get_lambda_client() should return the same cached instance "
            "to reuse TCP connections across requests"
        )

    def test_s3_client_uses_aws_region_env_var(self, monkeypatch):
        """Verify S3 client prefers AWS_REGION env var over settings."""
        from app.services.aws_clients import get_s3_client

        get_s3_client.cache_clear()
        monkeypatch.setenv("AWS_REGION", "eu-west-1")

        client = get_s3_client()

        assert client.meta.region_name == "eu-west-1"

    def test_sqs_client_uses_aws_region_env_var(self, monkeypatch):
        """Verify SQS client prefers AWS_REGION env var over settings."""
        from app.services.aws_clients import get_sqs_client

        get_sqs_client.cache_clear()
        monkeypatch.setenv("AWS_REGION", "eu-west-1")

        client = get_sqs_client()

        assert client.meta.region_name == "eu-west-1"

    def test_lambda_client_uses_aws_region_env_var(self, monkeypatch):
        """Verify Lambda client prefers AWS_REGION env var over settings."""
        from app.services.aws_clients import get_lambda_client

        get_lambda_client.cache_clear()
        monkeypatch.setenv("AWS_REGION", "eu-west-1")

        client = get_lambda_client()

        assert client.meta.region_name == "eu-west-1"


class TestBedrockClientCaching:
    """Tests for Bedrock client caching (kept separate due to specialized timeout config)."""

    def test_get_bedrock_client_returns_same_instance(self):
        """Verify get_bedrock_client returns cached instance on repeated calls."""
        from app.services.bedrock import get_bedrock_client

        get_bedrock_client.cache_clear()

        client1 = get_bedrock_client()
        client2 = get_bedrock_client()

        assert client1 is client2, (
            "get_bedrock_client() should return the same cached instance "
            "on repeated calls to avoid TCP connection overhead"
        )


class TestConsumerModulesUseAwsClients:
    """Tests verifying that consumer modules import from aws_clients."""

    def test_sqs_module_imports_get_sqs_client(self):
        """Verify sqs module imports get_sqs_client from aws_clients."""
        from app.services import sqs
        from app.services.aws_clients import get_sqs_client

        assert sqs.get_sqs_client is get_sqs_client

    def test_image_processing_imports_get_sqs_client(self):
        """Verify image_processing imports get_sqs_client from aws_clients."""
        from app.services import image_processing
        from app.services.aws_clients import get_sqs_client

        assert image_processing.get_sqs_client is get_sqs_client

    def test_tracking_dispatcher_imports_get_sqs_client(self):
        """Verify tracking_dispatcher imports get_sqs_client from aws_clients."""
        from app.services.aws_clients import get_sqs_client
        from app.workers import tracking_dispatcher

        assert tracking_dispatcher.get_sqs_client is get_sqs_client

    def test_scraper_imports_s3_and_lambda_clients(self):
        """Verify scraper imports both clients from aws_clients."""
        from app.services import scraper
        from app.services.aws_clients import get_lambda_client, get_s3_client

        assert scraper.get_s3_client is get_s3_client
        assert scraper.get_lambda_client is get_lambda_client

    def test_images_api_imports_get_s3_client(self):
        """Verify images API imports get_s3_client from aws_clients."""
        from app.api.v1 import images
        from app.services.aws_clients import get_s3_client

        assert images.get_s3_client is get_s3_client

    def test_bedrock_imports_get_s3_client(self):
        """Verify bedrock imports get_s3_client from aws_clients."""
        from app.services import bedrock
        from app.services.aws_clients import get_s3_client

        assert bedrock.get_s3_client is get_s3_client

    def test_fmv_lookup_imports_get_lambda_client(self):
        """Verify fmv_lookup imports get_lambda_client from aws_clients."""
        from app.services import fmv_lookup
        from app.services.aws_clients import get_lambda_client

        assert fmv_lookup.get_lambda_client is get_lambda_client
