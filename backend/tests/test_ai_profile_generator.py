"""Tests for AI profile generator Bedrock integration."""

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError


def _make_bedrock_response(content_text: str) -> dict:
    """Build a mock Bedrock invoke_model response."""
    body_bytes = json.dumps(
        {"content": [{"text": content_text}], "stop_reason": "end_turn"}
    ).encode()
    return {"body": BytesIO(body_bytes)}


def _make_empty_response() -> dict:
    """Build a mock Bedrock response with empty content."""
    body_bytes = json.dumps({"content": [], "stop_reason": "end_turn"}).encode()
    return {"body": BytesIO(body_bytes)}


def _make_throttle_error() -> ClientError:
    return ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
        "InvokeModel",
    )


class TestInvoke:
    """Tests for the _invoke helper."""

    @patch("app.services.ai_profile_generator.get_bedrock_client")
    def test_invoke_sends_correct_body(self, mock_get_client):
        from app.services.ai_profile_generator import _invoke

        mock_client = MagicMock()
        mock_client.invoke_model.return_value = _make_bedrock_response("hello")
        mock_get_client.return_value = mock_client

        result = _invoke("system prompt", "user prompt", max_tokens=512)

        assert result == "hello"
        call_args = mock_client.invoke_model.call_args
        body = json.loads(call_args.kwargs["body"])
        assert body["anthropic_version"] == "bedrock-2023-05-31"
        assert body["max_tokens"] == 512
        assert body["system"] == "system prompt"
        assert body["messages"] == [{"role": "user", "content": "user prompt"}]

    @patch("app.services.ai_profile_generator.get_bedrock_client")
    def test_invoke_empty_content_raises(self, mock_get_client):
        from app.services.ai_profile_generator import _invoke

        mock_client = MagicMock()
        mock_client.invoke_model.return_value = _make_empty_response()
        mock_get_client.return_value = mock_client

        with pytest.raises(ValueError, match="Empty content"):
            _invoke("sys", "user")

    @patch("app.services.ai_profile_generator.time")
    @patch("app.services.ai_profile_generator.get_bedrock_client")
    def test_invoke_retries_on_throttling(self, mock_get_client, mock_time):
        from app.services.ai_profile_generator import _invoke

        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = [
            _make_throttle_error(),
            _make_bedrock_response("ok after retry"),
        ]
        mock_get_client.return_value = mock_client
        mock_time.sleep = MagicMock()

        result = _invoke("sys", "user")
        assert result == "ok after retry"
        assert mock_client.invoke_model.call_count == 2
        mock_time.sleep.assert_called_once()

    @patch("app.services.ai_profile_generator.time")
    @patch("app.services.ai_profile_generator.get_bedrock_client")
    def test_invoke_raises_after_max_retries(self, mock_get_client, mock_time):
        from app.services.ai_profile_generator import _invoke

        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = _make_throttle_error()
        mock_get_client.return_value = mock_client
        mock_time.sleep = MagicMock()

        with pytest.raises(ClientError):
            _invoke("sys", "user")
        # 1 initial + 3 retries = 4 calls
        assert mock_client.invoke_model.call_count == 4

    @patch("app.services.ai_profile_generator.get_bedrock_client")
    def test_invoke_non_throttle_error_not_retried(self, mock_get_client):
        from app.services.ai_profile_generator import _invoke

        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Bad request"}},
            "InvokeModel",
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(ClientError):
            _invoke("sys", "user")
        assert mock_client.invoke_model.call_count == 1


class TestGetModelId:
    """Tests for model ID resolution."""

    def test_default_model(self):
        from app.services.ai_profile_generator import _get_model_id

        model_id = _get_model_id()
        assert "haiku" in model_id

    @patch.dict("os.environ", {"ENTITY_PROFILE_MODEL": "sonnet"})
    def test_env_override(self):
        from app.services.ai_profile_generator import _get_model_id

        model_id = _get_model_id()
        assert "sonnet" in model_id

    @patch.dict("os.environ", {"ENTITY_PROFILE_MODEL": "claude-3-5-haiku-20241022"})
    def test_unknown_model_falls_back_to_default(self):
        from app.services.ai_profile_generator import _get_model_id

        model_id = _get_model_id()
        assert "haiku" in model_id


class TestGenerateBioAndStories:
    """Tests for bio generation with Bedrock."""

    @patch("app.services.ai_profile_generator._invoke")
    def test_valid_response(self, mock_invoke):
        from app.services.ai_profile_generator import generate_bio_and_stories

        mock_invoke.return_value = json.dumps(
            {
                "biography": "A famous author.",
                "personal_stories": [
                    {"text": "A story", "year": 1850, "significance": "notable", "tone": "dramatic"}
                ],
            }
        )
        result = generate_bio_and_stories("Dickens", "author", birth_year=1812, death_year=1870)
        assert result["biography"] == "A famous author."
        assert len(result["personal_stories"]) == 1

    @patch("app.services.ai_profile_generator._invoke")
    def test_markdown_fenced_response(self, mock_invoke):
        from app.services.ai_profile_generator import generate_bio_and_stories

        mock_invoke.return_value = '```json\n{"biography": "Bio text", "personal_stories": []}\n```'
        result = generate_bio_and_stories("Test", "author")
        assert result["biography"] == "Bio text"

    @patch("app.services.ai_profile_generator._invoke")
    def test_invoke_failure_returns_fallback(self, mock_invoke):
        from app.services.ai_profile_generator import generate_bio_and_stories

        mock_invoke.side_effect = Exception("Bedrock down")
        result = generate_bio_and_stories("Test", "author")
        assert result == {"biography": None, "personal_stories": []}

    @patch("app.services.ai_profile_generator._invoke")
    def test_missing_biography_key(self, mock_invoke):
        from app.services.ai_profile_generator import generate_bio_and_stories

        mock_invoke.return_value = '{"personal_stories": []}'
        result = generate_bio_and_stories("Test", "author")
        assert result["biography"] is None
        assert result["personal_stories"] == []


class TestGenerateConnectionNarrative:
    """Tests for connection narrative generation."""

    @patch("app.services.ai_profile_generator._invoke")
    def test_returns_stripped_text(self, mock_invoke):
        from app.services.ai_profile_generator import generate_connection_narrative

        mock_invoke.return_value = "  A narrative sentence.  "
        result = generate_connection_narrative(
            "A", "author", "B", "publisher", "publisher", ["Book1"]
        )
        assert result == "A narrative sentence."

    @patch("app.services.ai_profile_generator._invoke")
    def test_failure_returns_none(self, mock_invoke):
        from app.services.ai_profile_generator import generate_connection_narrative

        mock_invoke.side_effect = Exception("fail")
        result = generate_connection_narrative("A", "author", "B", "publisher", "publisher", [])
        assert result is None

    @patch("app.services.ai_profile_generator._invoke")
    def test_empty_shared_books_uses_various_works(self, mock_invoke):
        from app.services.ai_profile_generator import generate_connection_narrative

        mock_invoke.return_value = "They collaborated on various works."
        generate_connection_narrative("A", "author", "B", "publisher", "publisher", [])
        prompt_arg = mock_invoke.call_args[0][1]
        assert "various works" in prompt_arg


class TestStripMarkdownFences:
    """Tests for _strip_markdown_fences helper."""

    def test_plain_json_passes_through(self):
        from app.services.ai_profile_generator import _strip_markdown_fences

        raw = '{"biography": "test", "personal_stories": []}'
        assert _strip_markdown_fences(raw) == raw

    def test_json_fenced_block_stripped(self):
        from app.services.ai_profile_generator import _strip_markdown_fences

        raw = '```json\n{"key": "value"}\n```'
        assert _strip_markdown_fences(raw) == '{"key": "value"}'

    def test_plain_fenced_block_stripped(self):
        from app.services.ai_profile_generator import _strip_markdown_fences

        raw = '```\n{"key": "value"}\n```'
        assert _strip_markdown_fences(raw) == '{"key": "value"}'

    def test_whitespace_around_fences_stripped(self):
        from app.services.ai_profile_generator import _strip_markdown_fences

        raw = '  ```json\n{"key": "value"}\n```  '
        assert _strip_markdown_fences(raw) == '{"key": "value"}'


class TestGenerateBioAndStoriesAdditional:
    """Additional edge-case tests for generate_bio_and_stories."""

    @patch("app.services.ai_profile_generator._invoke")
    def test_malformed_json_returns_safe_default(self, mock_invoke):
        from app.services.ai_profile_generator import generate_bio_and_stories

        mock_invoke.return_value = "not valid json at all {"
        result = generate_bio_and_stories("Test", "author")
        assert result == {"biography": None, "personal_stories": []}

    @patch("app.services.ai_profile_generator._invoke")
    def test_missing_personal_stories_defaults_to_empty_list(self, mock_invoke):
        from app.services.ai_profile_generator import generate_bio_and_stories

        mock_invoke.return_value = '{"biography": "A bio."}'
        result = generate_bio_and_stories("Test", "author")
        assert result["biography"] == "A bio."
        assert result["personal_stories"] == []

    @patch("app.services.ai_profile_generator._invoke")
    def test_personal_stories_non_list_defaults_to_empty(self, mock_invoke):
        from app.services.ai_profile_generator import generate_bio_and_stories

        mock_invoke.return_value = '{"biography": "A bio.", "personal_stories": "not a list"}'
        result = generate_bio_and_stories("Test", "author")
        assert result["biography"] == "A bio."
        assert result["personal_stories"] == []

    @patch("app.services.ai_profile_generator._invoke")
    def test_non_dict_response_returns_safe_default(self, mock_invoke):
        from app.services.ai_profile_generator import generate_bio_and_stories

        mock_invoke.return_value = '["a", "list", "instead"]'
        result = generate_bio_and_stories("Test", "author")
        assert result == {"biography": None, "personal_stories": []}

    @patch("app.services.ai_profile_generator._invoke")
    def test_book_titles_included_in_prompt(self, mock_invoke):
        from app.services.ai_profile_generator import generate_bio_and_stories

        mock_invoke.return_value = '{"biography": "Bio.", "personal_stories": []}'
        generate_bio_and_stories(
            "Dickens", "author", book_titles=["Oliver Twist", "Great Expectations"]
        )
        prompt_arg = mock_invoke.call_args[0][1]
        assert "Oliver Twist" in prompt_arg
        assert "Great Expectations" in prompt_arg

    @patch("app.services.ai_profile_generator._invoke")
    def test_founded_year_for_organization(self, mock_invoke):
        from app.services.ai_profile_generator import generate_bio_and_stories

        mock_invoke.return_value = '{"biography": "A publisher.", "personal_stories": []}'
        generate_bio_and_stories("Chapman and Hall", "publisher", founded_year=1830)
        prompt_arg = mock_invoke.call_args[0][1]
        assert "Founded: 1830" in prompt_arg


class TestGenerateRelationshipStory:
    """Tests for relationship story generation."""

    @patch("app.services.ai_profile_generator._invoke")
    def test_happy_path(self, mock_invoke):
        from app.services.ai_profile_generator import generate_relationship_story

        mock_invoke.return_value = json.dumps(
            {
                "summary": "Dickens published with Chapman and Hall.",
                "details": [
                    {
                        "text": "First novel published in 1836.",
                        "year": 1836,
                        "significance": "revelation",
                        "tone": "triumphant",
                    }
                ],
                "narrative_style": "timeline-events",
            }
        )
        result = generate_relationship_story(
            "Dickens",
            "author",
            "1812-1870",
            "Chapman and Hall",
            "publisher",
            "1830-1900",
            "publisher",
            ["Pickwick Papers"],
            "high_impact",
        )
        assert result is not None
        assert result["summary"] == "Dickens published with Chapman and Hall."
        assert len(result["details"]) == 1
        assert result["narrative_style"] == "timeline-events"

    @patch("app.services.ai_profile_generator._invoke")
    def test_missing_summary_returns_none(self, mock_invoke):
        from app.services.ai_profile_generator import generate_relationship_story

        mock_invoke.return_value = json.dumps(
            {"details": [{"text": "A fact."}], "narrative_style": "prose-paragraph"}
        )
        result = generate_relationship_story(
            "A", "author", "1800-1870", "B", "publisher", "1820-1900", "publisher", [], "high"
        )
        assert result is None

    @patch("app.services.ai_profile_generator._invoke")
    def test_missing_details_defaults_to_empty_list(self, mock_invoke):
        from app.services.ai_profile_generator import generate_relationship_story

        mock_invoke.return_value = json.dumps(
            {"summary": "A relationship.", "narrative_style": "bullet-facts"}
        )
        result = generate_relationship_story(
            "A", "author", "1800-1870", "B", "publisher", "1820-1900", "publisher", [], "high"
        )
        assert result is not None
        assert result["summary"] == "A relationship."
        assert result["details"] == []

    @patch("app.services.ai_profile_generator._invoke")
    def test_details_non_list_defaults_to_empty(self, mock_invoke):
        from app.services.ai_profile_generator import generate_relationship_story

        mock_invoke.return_value = json.dumps(
            {
                "summary": "A relationship.",
                "details": "not a list",
                "narrative_style": "prose-paragraph",
            }
        )
        result = generate_relationship_story(
            "A", "author", "1800-1870", "B", "publisher", "1820-1900", "publisher", [], "high"
        )
        assert result is not None
        assert result["details"] == []

    @patch("app.services.ai_profile_generator._invoke")
    def test_malformed_json_returns_none(self, mock_invoke):
        from app.services.ai_profile_generator import generate_relationship_story

        mock_invoke.return_value = "not valid json {"
        result = generate_relationship_story(
            "A", "author", "1800-1870", "B", "publisher", "1820-1900", "publisher", [], "high"
        )
        assert result is None

    @patch("app.services.ai_profile_generator._invoke")
    def test_non_dict_response_returns_none(self, mock_invoke):
        from app.services.ai_profile_generator import generate_relationship_story

        mock_invoke.return_value = '["a list instead"]'
        result = generate_relationship_story(
            "A", "author", "1800-1870", "B", "publisher", "1820-1900", "publisher", [], "high"
        )
        assert result is None

    @patch("app.services.ai_profile_generator._invoke")
    def test_api_exception_returns_none(self, mock_invoke):
        from app.services.ai_profile_generator import generate_relationship_story

        mock_invoke.side_effect = Exception("Bedrock unavailable")
        result = generate_relationship_story(
            "A", "author", "1800-1870", "B", "publisher", "1820-1900", "publisher", [], "high"
        )
        assert result is None

    @patch("app.services.ai_profile_generator._invoke")
    def test_markdown_fenced_response_parsed(self, mock_invoke):
        from app.services.ai_profile_generator import generate_relationship_story

        mock_invoke.return_value = (
            '```json\n{"summary": "Fenced.", "details": [], "narrative_style": "bullet-facts"}\n```'
        )
        result = generate_relationship_story(
            "A", "author", "1800-1870", "B", "publisher", "1820-1900", "publisher", [], "high"
        )
        assert result is not None
        assert result["summary"] == "Fenced."

    @patch("app.services.ai_profile_generator._invoke")
    def test_empty_shared_books_uses_various_works(self, mock_invoke):
        from app.services.ai_profile_generator import generate_relationship_story

        mock_invoke.return_value = json.dumps(
            {"summary": "A relationship.", "details": [], "narrative_style": "bullet-facts"}
        )
        generate_relationship_story(
            "A", "author", "1800-1870", "B", "publisher", "1820-1900", "publisher", [], "high"
        )
        prompt_arg = mock_invoke.call_args[0][1]
        assert "various works" in prompt_arg
