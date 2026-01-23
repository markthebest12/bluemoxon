"""Tests for boto3 client caching to avoid per-request client creation.

Issue #1241: Boto3 client reuse optimization.
"""


class TestBedrockClientCaching:
    """Tests for Bedrock client caching."""

    def test_get_bedrock_client_returns_same_instance(self):
        """Verify get_bedrock_client returns cached instance on repeated calls.

        Without caching, each call creates a new client with TCP connection overhead.
        With @lru_cache, the same client instance should be returned.
        """
        from app.services.bedrock import get_bedrock_client

        # Clear any cached instance
        get_bedrock_client.cache_clear()

        client1 = get_bedrock_client()
        client2 = get_bedrock_client()

        assert client1 is client2, (
            "get_bedrock_client() should return the same cached instance "
            "on repeated calls to avoid TCP connection overhead"
        )

    def test_get_s3_client_from_bedrock_returns_same_instance(self):
        """Verify get_s3_client in bedrock module returns cached instance."""
        from app.services.bedrock import get_s3_client

        # Clear any cached instance
        get_s3_client.cache_clear()

        client1 = get_s3_client()
        client2 = get_s3_client()

        assert client1 is client2, "get_s3_client() should return the same cached instance"


class TestSqsClientCaching:
    """Tests for SQS client caching."""

    def test_get_sqs_client_returns_same_instance(self):
        """Verify get_sqs_client returns cached instance on repeated calls."""
        from app.services.sqs import get_sqs_client

        # Clear any cached instance
        get_sqs_client.cache_clear()

        client1 = get_sqs_client()
        client2 = get_sqs_client()

        assert client1 is client2, (
            "get_sqs_client() should return the same cached instance "
            "to reuse TCP connections across requests"
        )


class TestImagesClientCaching:
    """Tests for images API S3 client caching."""

    def test_get_s3_client_returns_same_instance(self):
        """Verify get_s3_client in images API returns cached instance."""
        from app.api.v1.images import get_s3_client

        # Clear any cached instance
        get_s3_client.cache_clear()

        client1 = get_s3_client()
        client2 = get_s3_client()

        assert client1 is client2, "get_s3_client() should return the same cached instance"


class TestImageProcessingClientCaching:
    """Tests for image processing SQS client caching."""

    def test_get_sqs_client_returns_same_instance(self):
        """Verify get_sqs_client in image_processing returns cached instance."""
        from app.services.image_processing import get_sqs_client

        # Clear any cached instance
        get_sqs_client.cache_clear()

        client1 = get_sqs_client()
        client2 = get_sqs_client()

        assert client1 is client2, "get_sqs_client() should return the same cached instance"
