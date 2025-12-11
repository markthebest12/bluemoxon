"""Bedrock service tests."""

import pytest
from unittest.mock import MagicMock, patch


class TestPromptLoader:
    """Tests for prompt loading from S3."""

    def test_load_prompt_from_s3(self):
        """Test loading Napoleon framework prompt from S3."""
        from app.services.bedrock import load_napoleon_prompt

        # Should return a non-empty string
        prompt = load_napoleon_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "Napoleon" in prompt or "analysis" in prompt.lower()

    def test_prompt_cache(self):
        """Test that prompt is cached for 5 minutes."""
        from app.services.bedrock import load_napoleon_prompt, clear_prompt_cache

        # Clear any existing cache
        clear_prompt_cache()

        # First call populates cache
        prompt1 = load_napoleon_prompt()

        # Second call should return cached value
        prompt2 = load_napoleon_prompt()
        assert prompt1 == prompt2

        # Clean up
        clear_prompt_cache()


class TestBedrockClient:
    """Tests for Bedrock client."""

    def test_get_bedrock_client(self):
        """Test getting Bedrock runtime client."""
        from app.services.bedrock import get_bedrock_client

        client = get_bedrock_client()
        assert client is not None

    def test_model_id_mapping(self):
        """Test model name to ID mapping."""
        from app.services.bedrock import get_model_id

        assert get_model_id("sonnet") == "anthropic.claude-sonnet-4-5-20240929"
        assert get_model_id("opus") == "anthropic.claude-opus-4-5-20251101"
        assert get_model_id("invalid") == "anthropic.claude-sonnet-4-5-20240929"  # Default


class TestSourceUrlFetcher:
    """Tests for source URL content fetching."""

    @patch("app.services.bedrock.httpx.Client")
    def test_fetch_source_url_success(self, mock_client_class):
        """Test fetching content from a source URL."""
        from app.services.bedrock import fetch_source_url_content

        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.text = "<html><body>Test content</body></html>"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        content = fetch_source_url_content("https://example.com/test")
        assert content is not None
        assert len(content) > 0
        assert "Test content" in content

    def test_fetch_source_url_invalid(self):
        """Test handling invalid URL gracefully."""
        from app.services.bedrock import fetch_source_url_content

        content = fetch_source_url_content("https://invalid.nonexistent.url.test")
        assert content is None

    def test_fetch_source_url_none(self):
        """Test handling None URL."""
        from app.services.bedrock import fetch_source_url_content

        content = fetch_source_url_content(None)
        assert content is None

    def test_fetch_source_url_timeout(self):
        """Test timeout handling."""
        from app.services.bedrock import fetch_source_url_content

        # httpbin delay endpoint (but we have short timeout)
        content = fetch_source_url_content("https://httpbin.org/delay/10", timeout=1)
        assert content is None


class TestImageFetcher:
    """Tests for fetching book images for Bedrock."""

    def test_fetch_book_images_empty(self):
        """Test handling book with no images."""
        from app.services.bedrock import fetch_book_images_for_bedrock

        images = fetch_book_images_for_bedrock([])
        assert images == []

    def test_image_to_base64_format(self):
        """Test image data is formatted correctly for Bedrock."""
        from app.services.bedrock import format_image_for_bedrock
        import base64

        # Create a minimal valid JPEG
        test_data = b"\xff\xd8\xff\xe0\x00\x10JFIF"  # JPEG header

        result = format_image_for_bedrock(test_data, "image/jpeg")
        assert result["type"] == "image"
        assert result["source"]["type"] == "base64"
        assert result["source"]["media_type"] == "image/jpeg"
        # Should be valid base64
        decoded = base64.b64decode(result["source"]["data"])
        assert decoded == test_data
