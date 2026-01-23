"""Tests for boto3 client caching to avoid per-request client creation.

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


class TestBedrockClientCaching:
    """Tests for Bedrock client caching (kept separate due to specialized timeout config)."""

    def test_get_bedrock_client_returns_same_instance(self):
        """Verify get_bedrock_client returns cached instance on repeated calls.

        Without caching, each call creates a new client with TCP connection overhead.
        With @lru_cache, the same client instance should be returned.
        """
        from app.services.bedrock import get_bedrock_client

        get_bedrock_client.cache_clear()

        client1 = get_bedrock_client()
        client2 = get_bedrock_client()

        assert client1 is client2, (
            "get_bedrock_client() should return the same cached instance "
            "on repeated calls to avoid TCP connection overhead"
        )

    def test_get_s3_client_from_bedrock_delegates_to_aws_clients(self):
        """Verify get_s3_client in bedrock module delegates to aws_clients."""
        from app.services.aws_clients import get_s3_client as central_get_s3_client
        from app.services.bedrock import get_s3_client

        central_get_s3_client.cache_clear()

        bedrock_client = get_s3_client()
        central_client = central_get_s3_client()

        assert bedrock_client is central_client, (
            "bedrock.get_s3_client() should delegate to aws_clients.get_s3_client()"
        )


class TestModulesDelegateToAwsClients:
    """Tests verifying that consumer modules properly delegate to aws_clients."""

    def test_sqs_module_uses_central_sqs_client(self):
        """Verify sqs module uses central SQS client."""
        from app.services.aws_clients import get_sqs_client as central_get_sqs_client
        from app.services.sqs import get_sqs_client

        central_get_sqs_client.cache_clear()

        module_client = get_sqs_client()
        central_client = central_get_sqs_client()

        assert module_client is central_client, (
            "sqs.get_sqs_client() should delegate to aws_clients.get_sqs_client()"
        )

    def test_images_api_uses_central_s3_client(self):
        """Verify images API uses central S3 client."""
        from app.api.v1.images import get_s3_client
        from app.services.aws_clients import get_s3_client as central_get_s3_client

        central_get_s3_client.cache_clear()

        module_client = get_s3_client()
        central_client = central_get_s3_client()

        assert module_client is central_client, (
            "images.get_s3_client() should delegate to aws_clients.get_s3_client()"
        )

    def test_image_processing_uses_central_sqs_client(self):
        """Verify image_processing uses central SQS client."""
        from app.services.aws_clients import get_sqs_client as central_get_sqs_client
        from app.services.image_processing import get_sqs_client

        central_get_sqs_client.cache_clear()

        module_client = get_sqs_client()
        central_client = central_get_sqs_client()

        assert module_client is central_client, (
            "image_processing.get_sqs_client() should delegate to aws_clients.get_sqs_client()"
        )

    def test_scraper_uses_central_clients(self, monkeypatch):
        """Verify scraper module uses central S3 and Lambda clients."""
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

        from app.services.aws_clients import (
            get_lambda_client as central_get_lambda_client,
        )
        from app.services.aws_clients import (
            get_s3_client as central_get_s3_client,
        )
        from app.services.scraper import get_lambda_client, get_s3_client

        central_get_s3_client.cache_clear()
        central_get_lambda_client.cache_clear()

        scraper_s3 = get_s3_client()
        scraper_lambda = get_lambda_client()
        central_s3 = central_get_s3_client()
        central_lambda = central_get_lambda_client()

        assert scraper_s3 is central_s3, (
            "scraper.get_s3_client() should delegate to aws_clients.get_s3_client()"
        )
        assert scraper_lambda is central_lambda, (
            "scraper.get_lambda_client() should delegate to aws_clients.get_lambda_client()"
        )

    def test_fmv_lookup_uses_central_lambda_client(self, monkeypatch):
        """Verify FMV lookup uses central Lambda client."""
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

        from app.services.aws_clients import get_lambda_client as central_get_lambda_client
        from app.services.fmv_lookup import _get_lambda_client

        central_get_lambda_client.cache_clear()

        fmv_client = _get_lambda_client()
        central_client = central_get_lambda_client()

        assert fmv_client is central_client, (
            "fmv_lookup._get_lambda_client() should delegate to aws_clients.get_lambda_client()"
        )

    def test_tracking_dispatcher_uses_central_sqs_client(self, monkeypatch):
        """Verify tracking_dispatcher uses central SQS client."""
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

        from app.services.aws_clients import get_sqs_client as central_get_sqs_client
        from app.workers.tracking_dispatcher import get_sqs_client

        central_get_sqs_client.cache_clear()

        dispatcher_client = get_sqs_client()
        central_client = central_get_sqs_client()

        assert dispatcher_client is central_client, (
            "tracking_dispatcher.get_sqs_client() should delegate to aws_clients.get_sqs_client()"
        )
