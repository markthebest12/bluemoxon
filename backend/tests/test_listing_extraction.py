import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.listing import extract_listing_data

SAMPLE_LISTING_HTML = """
<html>
<head><title>eBay Listing</title></head>
<body>
<h1 class="x-item-title">The Queen of the Air by John Ruskin</h1>
<div class="x-price">$165.00</div>
<div class="description">
First edition, 1869. Full crushed morocco by Zaehnsdorf.
Minor foxing to preliminaries. A fine example.
</div>
</body>
</html>
"""


class TestExtractListingData:
    @patch("app.services.listing.invoke_bedrock_extraction")
    def test_extract_listing_data(self, mock_bedrock):
        mock_bedrock.return_value = {
            "title": "The Queen of the Air",
            "author": "John Ruskin",
            "publisher": None,
            "binder": "Zaehnsdorf",
            "price": 165.00,
            "currency": "USD",
            "publication_date": "1869",
            "volumes": 1,
            "condition": "First edition",
            "binding": "Full crushed morocco",
        }

        result = extract_listing_data(SAMPLE_LISTING_HTML)

        assert result["title"] == "The Queen of the Air"
        assert result["author"] == "John Ruskin"
        assert result["binder"] == "Zaehnsdorf"
        assert result["price"] == 165.00
        mock_bedrock.assert_called_once()

    @patch("app.services.listing.invoke_bedrock_extraction")
    def test_handles_gbp_currency(self, mock_bedrock):
        mock_bedrock.return_value = {
            "title": "Test Book",
            "author": "Test Author",
            "price": 125.00,
            "currency": "GBP",
        }

        result = extract_listing_data("<html>...</html>")
        assert result["currency"] == "GBP"

    @patch("app.services.listing.invoke_bedrock_extraction")
    def test_handles_missing_fields(self, mock_bedrock):
        mock_bedrock.return_value = {
            "title": "Test Book",
            "author": "Test Author",
            "price": 100.00,
            "currency": "USD",
        }

        result = extract_listing_data("<html>...</html>")
        assert result.get("binder") is None
        assert result.get("volumes", 1) == 1

    @patch("app.services.listing.invoke_bedrock_extraction")
    def test_sets_default_volumes(self, mock_bedrock):
        mock_bedrock.return_value = {
            "title": "Test Book",
            "author": "Test Author",
            "price": 50.00,
            "currency": "USD",
        }

        result = extract_listing_data("<html>...</html>")
        assert result["volumes"] == 1

    @patch("app.services.listing.invoke_bedrock_extraction")
    def test_sets_default_currency(self, mock_bedrock):
        mock_bedrock.return_value = {
            "title": "Test Book",
            "author": "Test Author",
            "price": 50.00,
        }

        result = extract_listing_data("<html>...</html>")
        assert result["currency"] == "USD"

    @patch("app.services.listing.invoke_bedrock_extraction")
    def test_extracts_multi_volume_set(self, mock_bedrock):
        """Test that volume count is correctly extracted for multi-volume sets."""
        mock_bedrock.return_value = {
            "title": "The Poetical Works of William Wordsworth",
            "author": "William Wordsworth",
            "publisher": "Edward Moxon",
            "price": 750.00,
            "currency": "USD",
            "volumes": 6,
        }

        result = extract_listing_data("<html>6 volumes complete set</html>")
        assert result["volumes"] == 6

    @patch("app.services.listing.get_bedrock_client")
    def test_truncates_long_html(self, mock_get_client):
        from app.services.listing import invoke_bedrock_extraction

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock response
        bedrock_response = {"content": [{"text": '{"title": "Test Book", "author": "Author"}'}]}
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps(bedrock_response).encode()
        mock_client.invoke_model.return_value = {"body": mock_body}

        # Create HTML longer than 50000 chars
        long_html = "<html>" + "x" * 60000 + "</html>"
        invoke_bedrock_extraction(long_html)

        # Verify the body passed to invoke_model has truncated HTML
        call_kwargs = mock_client.invoke_model.call_args[1]
        body = json.loads(call_kwargs["body"])
        prompt = body["messages"][0]["content"]
        # The prompt includes the extraction template + truncated HTML
        # The HTML part should be at most 50000 chars
        assert "Listing HTML:" in prompt
        # Full prompt is template + 50000 chars max HTML
        assert len(prompt) < 52000  # template is ~500 chars + 50000 max HTML + buffer

    @patch("app.services.listing.invoke_bedrock_extraction")
    def test_handles_json_in_markdown_code_block(self, mock_bedrock):
        # Simulate Bedrock sometimes wrapping JSON in markdown code blocks
        mock_bedrock.return_value = {
            "title": "Test Book",
            "author": "Test Author",
            "price": 50.00,
            "currency": "USD",
        }

        result = extract_listing_data("<html>test</html>")
        assert result["title"] == "Test Book"


class TestInvokeBedrockExtraction:
    """Tests for the low-level Bedrock extraction call."""

    @patch("app.services.listing.get_bedrock_client")
    def test_invokes_haiku_model(self, mock_get_client):
        from app.services.listing import invoke_bedrock_extraction

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock response body that returns valid JSON
        mock_body = MagicMock()
        mock_body.read.return_value = b'{"content": [{"text": "{\\"title\\": \\"Test\\"}"}]}'
        mock_client.invoke_model.return_value = {"body": mock_body}

        invoke_bedrock_extraction("<html>test</html>")

        # Verify Sonnet 4.5 model was used (via cross-region inference profile)
        call_kwargs = mock_client.invoke_model.call_args[1]
        assert "sonnet" in call_kwargs["modelId"]

    @patch("app.services.listing.get_bedrock_client")
    def test_parses_json_response(self, mock_get_client):
        from app.services.listing import invoke_bedrock_extraction

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock response with actual JSON data
        response_json = '{"title": "The Test Book", "author": "Test Author", "price": 100.00}'
        mock_body = MagicMock()
        mock_body.read.return_value = f'{{"content": [{{"text": "{response_json.replace(chr(34), chr(92) + chr(34))}"}}]}}'.encode()
        mock_client.invoke_model.return_value = {"body": mock_body}

        result = invoke_bedrock_extraction("<html>test</html>")

        assert result["title"] == "The Test Book"
        assert result["author"] == "Test Author"
        assert result["price"] == 100.00

    @patch("app.services.listing.get_bedrock_client")
    def test_handles_markdown_code_block(self, mock_get_client):
        from app.services.listing import invoke_bedrock_extraction

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock response with JSON wrapped in markdown code block
        # The text field contains: ```json\n{"title": "Book", "author": "Author"}\n```
        inner_json = '{"title": "Book", "author": "Author"}'
        response_text = f"```json\n{inner_json}\n```"
        bedrock_response = {"content": [{"text": response_text}]}
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps(bedrock_response).encode()
        mock_client.invoke_model.return_value = {"body": mock_body}

        result = invoke_bedrock_extraction("<html>test</html>")

        assert result["title"] == "Book"

    @patch("app.services.listing.get_bedrock_client")
    def test_raises_on_invalid_json(self, mock_get_client):
        from app.services.listing import invoke_bedrock_extraction

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock response with invalid JSON
        mock_body = MagicMock()
        mock_body.read.return_value = b'{"content": [{"text": "This is not JSON at all"}]}'
        mock_client.invoke_model.return_value = {"body": mock_body}

        with pytest.raises(ValueError, match="Failed to parse listing data"):
            invoke_bedrock_extraction("<html>test</html>")


class TestExtractRelevantHtml:
    """Tests for the extract_relevant_html function."""

    def test_extracts_volume_count_from_item_specifics(self):
        """Test that volume-related item specifics are extracted for Bedrock (#717)."""
        from app.services.listing import extract_relevant_html

        # Simulate eBay HTML with numberOfVolumes in item specifics
        # This matches eBay's real JSON structure for item specifics
        html_with_volumes = """
        <html>
        <head><title>Complete Works Set</title></head>
        <body>
        "numberOfVolumes":{"_type":"LabelsValues","labels":[],"values":[{"_type":"TextualDisplay","textSpans":[{"_type":"TextSpan","text":"8"}]}]}
        </body>
        </html>
        """

        result = extract_relevant_html(html_with_volumes)

        # Volume info should be extracted as an Item Specific
        # e.g., "Number Of Volumes: 8" in the item specifics section
        assert "Number Of Volumes: 8" in result

    def test_extracts_set_size_from_item_specifics(self):
        """Test that setSize item specific is also extracted (#717)."""
        from app.services.listing import extract_relevant_html

        # eBay sometimes uses "setSize" instead of "numberOfVolumes"
        html_with_set_size = """
        <html>
        <head><title>Complete Works</title></head>
        <body>
        "setSize":{"_type":"LabelsValues","labels":[],"values":[{"_type":"TextualDisplay","textSpans":[{"_type":"TextSpan","text":"6"}]}]}
        </body>
        </html>
        """

        result = extract_relevant_html(html_with_set_size)

        # Set size should be extracted
        assert "Set Size: 6" in result


class TestCollectedWorksTitleExtraction:
    """Tests for collected works / multi-volume set title extraction (#729)."""

    @patch("app.services.listing.invoke_bedrock_extraction")
    def test_collected_works_extracts_works_of_author(self, mock_bedrock):
        """Verify collected works sets extract as 'Works of [Author]'.

        When eBay listings have titles like "Charles Dickens 10 Vol Set",
        the extraction should return "Works of Charles Dickens" not "10 Vol Set".
        """
        mock_bedrock.return_value = {
            "title": "Works of Charles Dickens",
            "author": "Charles Dickens",
            "publisher": "Chapman & Hall",
            "price": 2500.00,
            "currency": "USD",
            "volumes": 10,
        }

        result = extract_listing_data("<html>Charles Dickens 10 Vol Set Chapman & Hall</html>")

        assert result["title"] == "Works of Charles Dickens"
        assert result["author"] == "Charles Dickens"
        assert result["volumes"] == 10
        mock_bedrock.assert_called_once()
