"""Tests for processed image note in AI prompts."""

from app.services.bedrock import PROCESSED_IMAGE_NOTE, build_bedrock_messages


class TestPromptLengthBaseline:
    """Measure current prompt lengths to establish baseline."""

    def test_processed_image_note_length(self):
        """Note should be approximately 180 characters."""
        assert len(PROCESSED_IMAGE_NOTE) < 250
        assert len(PROCESSED_IMAGE_NOTE) > 150

    def test_napoleon_prompt_has_headroom(self):
        """Napoleon prompt should have room for the note."""
        from app.services.bedrock import FALLBACK_PROMPT

        note_percentage = (len(PROCESSED_IMAGE_NOTE) / len(FALLBACK_PROMPT)) * 100
        assert note_percentage < 25

    def test_note_does_not_contain_special_characters(self):
        """Note should be plain text without markup that could break prompts."""
        assert "```" not in PROCESSED_IMAGE_NOTE
        assert "---" not in PROCESSED_IMAGE_NOTE
        assert "<" not in PROCESSED_IMAGE_NOTE
        assert ">" not in PROCESSED_IMAGE_NOTE


class TestProcessedImageNoteIntegration:
    """Test that note is properly included/excluded based on flag."""

    def test_note_included_when_primary_is_processed(self):
        """Note should be added to prompt when primary image is processed."""
        book_data = {"title": "Test Book"}
        images = [{"type": "image", "source": {"type": "base64", "data": "abc"}}]

        messages = build_bedrock_messages(
            book_data=book_data,
            images=images,
            source_content=None,
            primary_image_processed=True,
        )

        content_text = messages[0]["content"][0]["text"]
        assert PROCESSED_IMAGE_NOTE in content_text

    def test_note_excluded_when_primary_not_processed(self):
        """Note should NOT be added when primary image is not processed."""
        book_data = {"title": "Test Book"}
        images = [{"type": "image", "source": {"type": "base64", "data": "abc"}}]

        messages = build_bedrock_messages(
            book_data=book_data,
            images=images,
            source_content=None,
            primary_image_processed=False,
        )

        content_text = messages[0]["content"][0]["text"]
        assert PROCESSED_IMAGE_NOTE not in content_text

    def test_note_excluded_when_flag_not_provided(self):
        """Note should NOT be added when flag is not provided (backwards compat)."""
        book_data = {"title": "Test Book"}
        images = [{"type": "image", "source": {"type": "base64", "data": "abc"}}]

        messages = build_bedrock_messages(
            book_data=book_data,
            images=images,
            source_content=None,
        )

        content_text = messages[0]["content"][0]["text"]
        assert PROCESSED_IMAGE_NOTE not in content_text

    def test_prompt_structure_preserved_with_note(self):
        """All existing prompt sections should remain intact."""
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "publisher": "Test Publisher",
            "condition_notes": "Very good",
        }
        images = [{"type": "image", "source": {"type": "base64", "data": "abc"}}]

        messages = build_bedrock_messages(
            book_data=book_data,
            images=images,
            source_content=None,
            primary_image_processed=True,
        )

        content_text = messages[0]["content"][0]["text"]

        assert "## Book Metadata" in content_text
        assert "Title: Test Book" in content_text
        assert "Author: Test Author" in content_text
        assert "Publisher: Test Publisher" in content_text
        assert "## Images" in content_text
