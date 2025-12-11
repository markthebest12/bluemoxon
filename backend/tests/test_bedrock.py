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
        from app.services.bedrock import load_napoleon_prompt, _prompt_cache

        # First call populates cache
        prompt1 = load_napoleon_prompt()

        # Second call should return cached value
        prompt2 = load_napoleon_prompt()
        assert prompt1 == prompt2


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
