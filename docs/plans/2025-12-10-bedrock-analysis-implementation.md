# Bedrock Analysis Generation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add in-app Napoleon analysis generation using AWS Bedrock Claude models.

**Architecture:** Backend endpoint calls Bedrock with book metadata + images + source URL content. Prompts stored in S3 with 5-min cache. Frontend adds model dropdown and generate/regenerate buttons.

**Tech Stack:** FastAPI, boto3 (Bedrock Runtime), Vue 3, Pinia, TailwindCSS

---

## Prerequisites

Before starting implementation:

1. **AWS Bedrock access** - Ensure the Lambda execution role has `bedrock:InvokeModel` permission
2. **S3 bucket** - Use existing `bluemoxon-images` bucket or create dedicated prompts bucket
3. **Working directory** - `/Users/mark/projects/bluemoxon/.worktrees/acquisitions-dashboard`

---

## Task 1: Add Bedrock Client and Prompt Loader

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/bedrock.py`
- Create: `backend/tests/test_bedrock.py`

### Step 1: Create services directory

```bash
mkdir -p backend/app/services
touch backend/app/services/__init__.py
```

### Step 2: Write the failing test

Create `backend/tests/test_bedrock.py`:

```python
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
```

### Step 3: Run test to verify it fails

```bash
cd backend && python -m pytest tests/test_bedrock.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.bedrock'`

### Step 4: Write the implementation

Create `backend/app/services/bedrock.py`:

```python
"""AWS Bedrock service for AI-powered analysis generation."""

import json
import logging
import os
import time
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Model ID mapping
MODEL_IDS = {
    "sonnet": "anthropic.claude-sonnet-4-5-20240929",
    "opus": "anthropic.claude-opus-4-5-20251101",
}

# Prompt cache with TTL
_prompt_cache: dict = {"prompt": None, "timestamp": 0}
PROMPT_CACHE_TTL = 300  # 5 minutes

# S3 prompt location
PROMPTS_BUCKET = os.environ.get("PROMPTS_BUCKET", settings.images_bucket)
PROMPT_KEY = "prompts/napoleon-framework/v1.md"

# Fallback prompt if S3 unavailable
FALLBACK_PROMPT = """You are an expert antiquarian book appraiser generating a Napoleon framework analysis.

Generate a comprehensive book analysis following these sections:
1. Executive Summary (50-100 lines)
2. Detailed Condition Assessment (100-200 lines)
3. Comprehensive Market Analysis (150-300 lines)
4. Market Positioning & Victorian Binding Trends (100-150 lines)
5. Binding/Publisher Historical Context (100-200 lines)
6. Binding Elaborateness Classification (50-100 lines)
7. Rarity Assessment (50-100 lines)
8. Professional Valuation Methodology (100-150 lines)
9. Insurance Recommendations (50-75 lines)
10. Preservation and Care Guidelines (75-125 lines)
11. Value Enhancement/Detraction Factors (75-100 lines)
12. Conclusions and Recommendations (50-100 lines)
13. Methodology Statement and Disclaimers (50-75 lines)

Minimum 500 lines for standard items, 700+ for high-value items.
Use markdown formatting with headers, bullet points, and tables where appropriate.
"""


def get_bedrock_client():
    """Get Bedrock runtime client."""
    region = os.environ.get("AWS_REGION", settings.aws_region)
    return boto3.client("bedrock-runtime", region_name=region)


def get_s3_client():
    """Get S3 client."""
    region = os.environ.get("AWS_REGION", settings.aws_region)
    return boto3.client("s3", region_name=region)


def get_model_id(model_name: str) -> str:
    """Get Bedrock model ID from friendly name."""
    return MODEL_IDS.get(model_name, MODEL_IDS["sonnet"])


def load_napoleon_prompt() -> str:
    """Load Napoleon framework prompt from S3 with caching.

    Returns cached prompt if still valid, otherwise fetches from S3.
    Falls back to hardcoded prompt if S3 unavailable.
    """
    global _prompt_cache

    current_time = time.time()

    # Return cached prompt if still valid
    if _prompt_cache["prompt"] and (current_time - _prompt_cache["timestamp"]) < PROMPT_CACHE_TTL:
        logger.debug("Using cached Napoleon prompt")
        return _prompt_cache["prompt"]

    # Try to load from S3
    try:
        s3 = get_s3_client()
        response = s3.get_object(Bucket=PROMPTS_BUCKET, Key=PROMPT_KEY)
        prompt = response["Body"].read().decode("utf-8")
        logger.info(f"Loaded Napoleon prompt from s3://{PROMPTS_BUCKET}/{PROMPT_KEY}")

        # Update cache
        _prompt_cache = {"prompt": prompt, "timestamp": current_time}
        return prompt

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.warning(f"Failed to load prompt from S3 ({error_code}), using fallback")
        return FALLBACK_PROMPT
    except Exception as e:
        logger.warning(f"Error loading prompt from S3: {e}, using fallback")
        return FALLBACK_PROMPT


def clear_prompt_cache():
    """Clear the prompt cache (useful for testing)."""
    global _prompt_cache
    _prompt_cache = {"prompt": None, "timestamp": 0}
```

### Step 5: Run test to verify it passes

```bash
cd backend && python -m pytest tests/test_bedrock.py -v
```

Expected: PASS (3 tests)

### Step 6: Commit

```bash
git add backend/app/services/ backend/tests/test_bedrock.py
git commit -m "feat: add Bedrock client and prompt loader service"
```

---

## Task 2: Add Source URL Fetcher

**Files:**
- Modify: `backend/app/services/bedrock.py`
- Modify: `backend/tests/test_bedrock.py`

### Step 1: Write the failing test

Add to `backend/tests/test_bedrock.py`:

```python
class TestSourceUrlFetcher:
    """Tests for source URL content fetching."""

    def test_fetch_source_url_success(self):
        """Test fetching content from a source URL."""
        from app.services.bedrock import fetch_source_url_content

        # Use a known stable URL for testing
        content = fetch_source_url_content("https://httpbin.org/html")
        assert content is not None
        assert len(content) > 0

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
```

### Step 2: Run test to verify it fails

```bash
cd backend && python -m pytest tests/test_bedrock.py::TestSourceUrlFetcher -v
```

Expected: FAIL with `ImportError: cannot import name 'fetch_source_url_content'`

### Step 3: Write the implementation

Add to `backend/app/services/bedrock.py`:

```python
import httpx


def fetch_source_url_content(url: str | None, timeout: int = 15) -> str | None:
    """Fetch content from a source URL (eBay listing, AbeBooks, etc).

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Text content of the page, or None if fetch failed
    """
    if not url:
        return None

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; BlueMoxon/1.0)"
            })
            response.raise_for_status()

            # Return text content (HTML)
            content = response.text

            # Truncate if too long (Bedrock has token limits)
            max_chars = 50000  # ~12k tokens
            if len(content) > max_chars:
                content = content[:max_chars] + "\n\n[Content truncated...]"

            logger.info(f"Fetched {len(content)} chars from {url}")
            return content

    except httpx.TimeoutException:
        logger.warning(f"Timeout fetching {url}")
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error fetching {url}: {e.response.status_code}")
        return None
    except Exception as e:
        logger.warning(f"Error fetching {url}: {e}")
        return None
```

### Step 4: Run test to verify it passes

```bash
cd backend && python -m pytest tests/test_bedrock.py::TestSourceUrlFetcher -v
```

Expected: PASS (4 tests)

### Step 5: Commit

```bash
git add backend/app/services/bedrock.py backend/tests/test_bedrock.py
git commit -m "feat: add source URL content fetcher for Bedrock context"
```

---

## Task 3: Add Image Fetcher for Bedrock

**Files:**
- Modify: `backend/app/services/bedrock.py`
- Modify: `backend/tests/test_bedrock.py`

### Step 1: Write the failing test

Add to `backend/tests/test_bedrock.py`:

```python
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
```

### Step 2: Run test to verify it fails

```bash
cd backend && python -m pytest tests/test_bedrock.py::TestImageFetcher -v
```

Expected: FAIL with `ImportError`

### Step 3: Write the implementation

Add to `backend/app/services/bedrock.py`:

```python
import base64
from app.models import BookImage


def format_image_for_bedrock(image_data: bytes, media_type: str) -> dict:
    """Format image data for Bedrock Claude message API.

    Args:
        image_data: Raw image bytes
        media_type: MIME type (e.g., "image/jpeg")

    Returns:
        Dict in Bedrock image content block format
    """
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.b64encode(image_data).decode("utf-8"),
        },
    }


def fetch_book_images_for_bedrock(
    images: list[BookImage],
    max_images: int = 10,
) -> list[dict]:
    """Fetch book images from S3 and format for Bedrock.

    Args:
        images: List of BookImage objects
        max_images: Maximum number of images to include

    Returns:
        List of Bedrock-formatted image content blocks
    """
    if not images:
        return []

    result = []
    s3 = get_s3_client()
    bucket = os.environ.get("IMAGES_BUCKET", settings.images_bucket)

    # Sort by display_order and take max_images
    sorted_images = sorted(images, key=lambda x: x.display_order)[:max_images]

    for img in sorted_images:
        try:
            # Fetch from S3
            s3_key = f"books/{img.s3_key}"
            response = s3.get_object(Bucket=bucket, Key=s3_key)
            image_data = response["Body"].read()

            # Determine media type from content type or filename
            content_type = response.get("ContentType", "image/jpeg")
            if img.s3_key.lower().endswith(".png"):
                content_type = "image/png"
            elif img.s3_key.lower().endswith((".jpg", ".jpeg")):
                content_type = "image/jpeg"

            result.append(format_image_for_bedrock(image_data, content_type))
            logger.debug(f"Loaded image {img.s3_key} for Bedrock")

        except Exception as e:
            logger.warning(f"Failed to load image {img.s3_key}: {e}")
            continue

    logger.info(f"Loaded {len(result)} images for Bedrock analysis")
    return result
```

### Step 4: Run test to verify it passes

```bash
cd backend && python -m pytest tests/test_bedrock.py::TestImageFetcher -v
```

Expected: PASS (2 tests)

### Step 5: Commit

```bash
git add backend/app/services/bedrock.py backend/tests/test_bedrock.py
git commit -m "feat: add image fetcher for Bedrock analysis context"
```

---

## Task 4: Add Bedrock Invoke Function

**Files:**
- Modify: `backend/app/services/bedrock.py`
- Modify: `backend/tests/test_bedrock.py`

### Step 1: Write the failing test

Add to `backend/tests/test_bedrock.py`:

```python
from unittest.mock import MagicMock, patch


class TestBedrockInvoke:
    """Tests for Bedrock model invocation."""

    def test_build_messages_metadata_only(self):
        """Test building messages with just metadata."""
        from app.services.bedrock import build_bedrock_messages

        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "publisher": "Test Publisher",
            "publication_date": "1867",
        }

        messages = build_bedrock_messages(book_data, [], None)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        # Content should include book metadata
        content_text = messages[0]["content"][0]["text"]
        assert "Test Book" in content_text
        assert "Test Author" in content_text

    def test_build_messages_with_images(self):
        """Test building messages with images."""
        from app.services.bedrock import build_bedrock_messages

        book_data = {"title": "Test Book"}
        images = [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "abc123"}}
        ]

        messages = build_bedrock_messages(book_data, images, None)
        content = messages[0]["content"]
        # Should have text + image blocks
        assert len(content) >= 2
        assert any(c.get("type") == "image" for c in content)

    @patch("app.services.bedrock.get_bedrock_client")
    def test_invoke_bedrock_success(self, mock_get_client):
        """Test successful Bedrock invocation."""
        from app.services.bedrock import invoke_bedrock

        # Mock response
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = {
            "body": MagicMock(read=lambda: b'{"content": [{"text": "# Analysis\\n\\nTest content"}]}')
        }
        mock_get_client.return_value = mock_client

        result = invoke_bedrock(
            messages=[{"role": "user", "content": [{"type": "text", "text": "test"}]}],
            model="sonnet",
        )

        assert "# Analysis" in result
        mock_client.invoke_model.assert_called_once()
```

### Step 2: Run test to verify it fails

```bash
cd backend && python -m pytest tests/test_bedrock.py::TestBedrockInvoke -v
```

Expected: FAIL with `ImportError`

### Step 3: Write the implementation

Add to `backend/app/services/bedrock.py`:

```python
def build_bedrock_messages(
    book_data: dict,
    images: list[dict],
    source_content: str | None,
) -> list[dict]:
    """Build messages array for Bedrock Claude API.

    Args:
        book_data: Dict with book metadata
        images: List of Bedrock-formatted image blocks
        source_content: Optional HTML content from source URL

    Returns:
        Messages array for Bedrock invoke_model
    """
    # Build the text prompt with book metadata
    text_parts = ["Analyze this book for the collection:\n\n## Book Metadata"]

    if book_data.get("title"):
        text_parts.append(f"- Title: {book_data['title']}")
    if book_data.get("author"):
        text_parts.append(f"- Author: {book_data['author']}")
    if book_data.get("publisher"):
        publisher = book_data["publisher"]
        tier = book_data.get("publisher_tier", "")
        text_parts.append(f"- Publisher: {publisher}" + (f" (Tier: {tier})" if tier else ""))
    if book_data.get("publication_date"):
        text_parts.append(f"- Publication Date: {book_data['publication_date']}")
    if book_data.get("volumes"):
        text_parts.append(f"- Volumes: {book_data['volumes']}")
    if book_data.get("binding_type"):
        text_parts.append(f"- Binding Type: {book_data['binding_type']}")
    if book_data.get("binder"):
        text_parts.append(f"- Binder: {book_data['binder']} (authenticated)")
    if book_data.get("condition_notes"):
        text_parts.append(f"- Condition Notes: {book_data['condition_notes']}")
    if book_data.get("purchase_price"):
        text_parts.append(f"- Purchase/Asking Price: ${book_data['purchase_price']}")

    # Add source listing content if available
    if source_content:
        text_parts.append("\n## Source Listing\n")
        text_parts.append(source_content)

    # Add image instructions if images provided
    if images:
        text_parts.append(f"\n## Images\n{len(images)} images are attached below.")

    user_text = "\n".join(text_parts)

    # Build content array with text first, then images
    content = [{"type": "text", "text": user_text}]
    content.extend(images)

    return [{"role": "user", "content": content}]


def invoke_bedrock(
    messages: list[dict],
    model: str = "sonnet",
    max_tokens: int = 16000,
) -> str:
    """Invoke Bedrock Claude model and return response text.

    Args:
        messages: Messages array for Claude
        model: Model name ("sonnet" or "opus")
        max_tokens: Maximum tokens in response

    Returns:
        Generated text response

    Raises:
        Exception: If Bedrock invocation fails
    """
    client = get_bedrock_client()
    model_id = get_model_id(model)
    system_prompt = load_napoleon_prompt()

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": messages,
    })

    logger.info(f"Invoking Bedrock model {model_id}")

    response = client.invoke_model(
        modelId=model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )

    response_body = json.loads(response["body"].read())
    result_text = response_body["content"][0]["text"]

    logger.info(f"Bedrock returned {len(result_text)} chars")
    return result_text
```

### Step 4: Run test to verify it passes

```bash
cd backend && python -m pytest tests/test_bedrock.py::TestBedrockInvoke -v
```

Expected: PASS (3 tests)

### Step 5: Commit

```bash
git add backend/app/services/bedrock.py backend/tests/test_bedrock.py
git commit -m "feat: add Bedrock message builder and invoke function"
```

---

## Task 5: Add Generate Analysis API Endpoint

**Files:**
- Modify: `backend/app/api/v1/books.py`
- Create: `backend/tests/test_generate_analysis.py`

### Step 1: Write the failing test

Create `backend/tests/test_generate_analysis.py`:

```python
"""Generate analysis API tests."""

from unittest.mock import patch, MagicMock
import pytest


class TestGenerateAnalysis:
    """Tests for POST /api/v1/books/{id}/analysis/generate."""

    def test_generate_analysis_book_not_found(self, client):
        """Test 404 when book doesn't exist."""
        response = client.post("/api/v1/books/999/analysis/generate")
        assert response.status_code == 404

    @patch("app.api.v1.books.invoke_bedrock")
    @patch("app.api.v1.books.fetch_book_images_for_bedrock")
    @patch("app.api.v1.books.fetch_source_url_content")
    def test_generate_analysis_success(
        self,
        mock_fetch_url,
        mock_fetch_images,
        mock_invoke,
        client,
    ):
        """Test successful analysis generation."""
        # Setup mocks
        mock_fetch_url.return_value = None
        mock_fetch_images.return_value = []
        mock_invoke.return_value = """# Executive Summary

This is a test analysis generated by Bedrock.

## Condition Assessment

The book is in very good condition.
"""

        # Create a book
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Generate analysis
        response = client.post(f"/api/v1/books/{book_id}/analysis/generate")
        assert response.status_code == 200
        data = response.json()
        assert data["book_id"] == book_id
        assert "Executive Summary" in data["full_markdown"]
        assert data["model_used"] is not None

    @patch("app.api.v1.books.invoke_bedrock")
    @patch("app.api.v1.books.fetch_book_images_for_bedrock")
    @patch("app.api.v1.books.fetch_source_url_content")
    def test_generate_analysis_replaces_existing(
        self,
        mock_fetch_url,
        mock_fetch_images,
        mock_invoke,
        client,
    ):
        """Test that generating analysis replaces existing."""
        mock_fetch_url.return_value = None
        mock_fetch_images.return_value = []
        mock_invoke.return_value = "# New Analysis\n\nReplacement content."

        # Create a book with existing analysis
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Add initial analysis
        client.put(
            f"/api/v1/books/{book_id}/analysis",
            content="# Old Analysis",
            headers={"Content-Type": "text/plain"},
        )

        # Generate new analysis (should replace)
        response = client.post(f"/api/v1/books/{book_id}/analysis/generate")
        assert response.status_code == 200

        # Verify old analysis was replaced
        response = client.get(f"/api/v1/books/{book_id}/analysis/raw")
        assert "New Analysis" in response.text
        assert "Old Analysis" not in response.text

    def test_generate_analysis_model_selection(self, client):
        """Test model parameter is accepted."""
        # Create a book
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Test with opus model (will fail without mock, but validates param handling)
        with patch("app.api.v1.books.invoke_bedrock") as mock_invoke:
            with patch("app.api.v1.books.fetch_book_images_for_bedrock") as mock_images:
                with patch("app.api.v1.books.fetch_source_url_content") as mock_url:
                    mock_url.return_value = None
                    mock_images.return_value = []
                    mock_invoke.return_value = "# Test"

                    response = client.post(
                        f"/api/v1/books/{book_id}/analysis/generate",
                        json={"model": "opus"},
                    )
                    assert response.status_code == 200

                    # Verify opus model was requested
                    call_args = mock_invoke.call_args
                    assert call_args[1]["model"] == "opus"
```

### Step 2: Run test to verify it fails

```bash
cd backend && python -m pytest tests/test_generate_analysis.py -v
```

Expected: FAIL (endpoint doesn't exist)

### Step 3: Write the implementation

Add to `backend/app/api/v1/books.py` (at the top, add imports):

```python
from app.services.bedrock import (
    build_bedrock_messages,
    fetch_book_images_for_bedrock,
    fetch_source_url_content,
    get_model_id,
    invoke_bedrock,
)
```

Add new endpoint (after existing analysis endpoints, around line 750):

```python
class GenerateAnalysisRequest(BaseModel):
    """Request body for analysis generation."""

    model: str = "sonnet"  # "sonnet" or "opus"


@router.post("/{book_id}/analysis/generate")
def generate_analysis(
    book_id: int,
    request: GenerateAnalysisRequest = Body(default=GenerateAnalysisRequest()),
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    """Generate Napoleon-style analysis using AWS Bedrock.

    Requires admin role. Replaces existing analysis if present.
    """
    from datetime import UTC, datetime

    from app.models import BookAnalysis
    from app.utils.markdown_parser import parse_analysis_markdown

    # Get book with relationships
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Build book metadata dict
    book_data = {
        "title": book.title,
        "author": book.author.name if book.author else None,
        "publisher": book.publisher.name if book.publisher else None,
        "publisher_tier": book.publisher.tier if book.publisher else None,
        "publication_date": book.publication_date,
        "volumes": book.volumes,
        "binding_type": book.binding_type,
        "binder": book.binder.name if book.binder else None,
        "condition_notes": book.condition_notes,
        "purchase_price": float(book.purchase_price) if book.purchase_price else None,
    }

    # Fetch source URL content if available
    source_content = fetch_source_url_content(book.source_url)

    # Fetch images
    images = fetch_book_images_for_bedrock(book.images)

    # Build messages and invoke Bedrock
    messages = build_bedrock_messages(book_data, images, source_content)
    model_id = get_model_id(request.model)

    try:
        analysis_text = invoke_bedrock(messages, model=request.model)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Bedrock invocation failed: {str(e)}",
        ) from e

    # Parse markdown to extract structured fields
    parsed = parse_analysis_markdown(analysis_text)

    # Delete existing analysis if present
    if book.analysis:
        db.delete(book.analysis)
        db.flush()

    # Create new analysis
    analysis = BookAnalysis(
        book_id=book_id,
        full_markdown=analysis_text,
        executive_summary=parsed.executive_summary,
        historical_significance=parsed.historical_significance,
        condition_assessment=parsed.condition_assessment,
        market_analysis=parsed.market_analysis,
        recommendations=parsed.recommendations,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return {
        "id": analysis.id,
        "book_id": book_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "model_used": model_id,
        "full_markdown": analysis_text,
        "executive_summary": analysis.executive_summary,
        "condition_assessment": analysis.condition_assessment,
        "market_analysis": analysis.market_analysis,
        "historical_significance": analysis.historical_significance,
        "recommendations": analysis.recommendations,
    }
```

Also add import for `require_admin` at top of file:

```python
from app.auth import require_admin, require_editor
```

And add BaseModel import:

```python
from pydantic import BaseModel
```

### Step 4: Run test to verify it passes

```bash
cd backend && python -m pytest tests/test_generate_analysis.py -v
```

Expected: PASS (4 tests)

### Step 5: Commit

```bash
git add backend/app/api/v1/books.py backend/tests/test_generate_analysis.py
git commit -m "feat: add POST /books/{id}/analysis/generate endpoint"
```

---

## Task 6: Update conftest for Admin Mock

**Files:**
- Modify: `backend/tests/conftest.py`

### Step 1: Add admin mock to conftest

The generate endpoint requires admin role. Update `backend/tests/conftest.py`:

```python
"""Test fixtures and configuration."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import CurrentUser, require_admin, require_editor
from app.db import get_db
from app.main import app
from app.models.base import Base


# Mock editor user for tests
def get_mock_editor():
    """Return a mock editor user for tests."""
    return CurrentUser(
        cognito_sub="test-user-123",
        email="test@example.com",
        role="editor",
        db_user=None,
    )


# Mock admin user for tests
def get_mock_admin():
    """Return a mock admin user for tests."""
    return CurrentUser(
        cognito_sub="test-admin-123",
        email="admin@example.com",
        role="admin",
        db_user=None,
    )


# Use DATABASE_URL from environment (CI uses PostgreSQL) or SQLite for local
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # PostgreSQL in CI
    engine = create_engine(DATABASE_URL)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    # SQLite in-memory for fast local tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client with database override and mock auth."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_editor] = get_mock_editor
    app.dependency_overrides[require_admin] = get_mock_admin
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
```

### Step 2: Run all tests to verify nothing broke

```bash
cd backend && python -m pytest -v
```

Expected: All tests pass

### Step 3: Commit

```bash
git add backend/tests/conftest.py
git commit -m "test: add admin mock to conftest for generate endpoint tests"
```

---

## Task 7: Add Frontend Books Store Action

**Files:**
- Modify: `frontend/src/stores/books.ts`
- Create: `frontend/src/stores/__tests__/books-generate.spec.ts`

### Step 1: Write the failing test

Create `frontend/src/stores/__tests__/books-generate.spec.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useBooksStore } from "../books";

// Mock the API
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import { api } from "@/services/api";

describe("books store - generateAnalysis", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("generates analysis with default model", async () => {
    const mockResponse = {
      data: {
        id: 1,
        book_id: 42,
        model_used: "anthropic.claude-sonnet-4-5-20240929",
        full_markdown: "# Test Analysis",
      },
    };
    vi.mocked(api.post).mockResolvedValue(mockResponse);

    const store = useBooksStore();
    const result = await store.generateAnalysis(42);

    expect(api.post).toHaveBeenCalledWith("/books/42/analysis/generate", {
      model: "sonnet",
    });
    expect(result.full_markdown).toBe("# Test Analysis");
  });

  it("generates analysis with opus model", async () => {
    const mockResponse = {
      data: {
        id: 1,
        book_id: 42,
        model_used: "anthropic.claude-opus-4-5-20251101",
        full_markdown: "# Opus Analysis",
      },
    };
    vi.mocked(api.post).mockResolvedValue(mockResponse);

    const store = useBooksStore();
    await store.generateAnalysis(42, "opus");

    expect(api.post).toHaveBeenCalledWith("/books/42/analysis/generate", {
      model: "opus",
    });
  });

  it("updates currentBook.has_analysis on success", async () => {
    const mockResponse = {
      data: {
        id: 1,
        book_id: 42,
        full_markdown: "# Test",
      },
    };
    vi.mocked(api.post).mockResolvedValue(mockResponse);

    const store = useBooksStore();
    store.currentBook = { id: 42, title: "Test", has_analysis: false } as any;

    await store.generateAnalysis(42);

    expect(store.currentBook?.has_analysis).toBe(true);
  });
});
```

### Step 2: Run test to verify it fails

```bash
cd frontend && npm test -- --run src/stores/__tests__/books-generate.spec.ts
```

Expected: FAIL with `store.generateAnalysis is not a function`

### Step 3: Write the implementation

Add to `frontend/src/stores/books.ts` (inside the store definition, after other actions):

```typescript
async function generateAnalysis(
  bookId: number,
  model: "sonnet" | "opus" = "sonnet"
): Promise<{
  id: number;
  book_id: number;
  model_used: string;
  full_markdown: string;
  generated_at: string;
}> {
  const response = await api.post(`/books/${bookId}/analysis/generate`, {
    model,
  });

  // Update currentBook if it matches
  if (currentBook.value?.id === bookId) {
    currentBook.value.has_analysis = true;
  }

  return response.data;
}
```

And add to the return statement:

```typescript
return {
  // ... existing exports
  generateAnalysis,
};
```

### Step 4: Run test to verify it passes

```bash
cd frontend && npm test -- --run src/stores/__tests__/books-generate.spec.ts
```

Expected: PASS (3 tests)

### Step 5: Commit

```bash
git add frontend/src/stores/books.ts frontend/src/stores/__tests__/books-generate.spec.ts
git commit -m "feat: add generateAnalysis action to books store"
```

---

## Task 8: Add Generate Button to AnalysisViewer

**Files:**
- Modify: `frontend/src/components/books/AnalysisViewer.vue`

### Step 1: Update AnalysisViewer component

Add the generate controls to `frontend/src/components/books/AnalysisViewer.vue`.

First, add new refs and imports at the top of the script:

```typescript
// Add to existing imports
import { useBooksStore } from "@/stores/books";

// Add new refs (after existing refs around line 30)
const selectedModel = ref<"sonnet" | "opus">("sonnet");
const generating = ref(false);
const generateError = ref<string | null>(null);

const booksStore = useBooksStore();
```

Add the generate function:

```typescript
async function generateAnalysis() {
  if (generating.value) return;

  generating.value = true;
  generateError.value = null;
  error.value = null;

  try {
    const result = await booksStore.generateAnalysis(props.bookId, selectedModel.value);
    analysis.value = result.full_markdown;
    editedAnalysis.value = result.full_markdown;
  } catch (e: any) {
    generateError.value =
      e.response?.data?.detail || e.message || "Failed to generate analysis.";
  } finally {
    generating.value = false;
  }
}
```

Update the template to add generate controls. In the header section (around line 198), add after the existing edit controls:

```vue
<!-- Generate controls (admin only, when no analysis or in view mode) -->
<template v-if="canEdit && !editMode">
  <div class="flex items-center gap-2">
    <select
      v-model="selectedModel"
      class="text-sm border border-gray-300 rounded px-2 py-1"
      :disabled="generating"
    >
      <option value="sonnet">Sonnet 4.5</option>
      <option value="opus">Opus 4.5</option>
    </select>
    <button
      @click="generateAnalysis"
      :disabled="generating"
      class="btn-primary text-sm"
    >
      <span v-if="generating" class="flex items-center gap-2">
        <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24">
          <circle
            class="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
            fill="none"
          />
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
        Generating...
      </span>
      <span v-else>{{ analysis ? '🔄 Regenerate' : '⚡ Generate' }}</span>
    </button>
  </div>
</template>
```

Add error display for generation errors (after the existing error display):

```vue
<div
  v-if="generateError"
  class="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm"
>
  {{ generateError }}
</div>
```

### Step 2: Run tests and build

```bash
cd frontend && npm run type-check && npm run build
```

Expected: No errors

### Step 3: Commit

```bash
git add frontend/src/components/books/AnalysisViewer.vue
git commit -m "feat: add generate/regenerate button to AnalysisViewer"
```

---

## Task 9: Add Generate Button to AcquisitionsView

**Files:**
- Modify: `frontend/src/views/AcquisitionsView.vue`

### Step 1: Add generate action to EVALUATING cards

In `AcquisitionsView.vue`, add a generate analysis button to the EVALUATING column cards.

Find the EVALUATING column template (around line 140) and add after the existing buttons:

```vue
<!-- Generate Analysis button (EVALUATING items) -->
<button
  v-if="authStore.isAdmin"
  @click="handleGenerateAnalysis(item)"
  :disabled="generatingAnalysis === item.id"
  class="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
>
  <span v-if="generatingAnalysis === item.id">Generating...</span>
  <span v-else>{{ item.has_analysis ? '🔄' : '⚡' }} Analysis</span>
</button>
```

Add the state and handler in the script:

```typescript
// Add ref
const generatingAnalysis = ref<number | null>(null);

// Add handler
async function handleGenerateAnalysis(item: AcquisitionItem) {
  if (generatingAnalysis.value) return;

  generatingAnalysis.value = item.id;
  try {
    await booksStore.generateAnalysis(item.id);
    // Refresh the item to show has_analysis = true
    await fetchAll();
  } catch (e: any) {
    console.error("Failed to generate analysis:", e);
    // Could add toast notification here
  } finally {
    generatingAnalysis.value = null;
  }
}
```

### Step 2: Run tests and build

```bash
cd frontend && npm run type-check && npm run build
```

Expected: No errors

### Step 3: Commit

```bash
git add frontend/src/views/AcquisitionsView.vue
git commit -m "feat: add generate analysis button to acquisitions dashboard"
```

---

## Task 10: Upload Napoleon Prompt to S3

**Files:**
- Create: `infrastructure/prompts/napoleon-framework/v1.md`

### Step 1: Create the prompt file

Create directory and file:

```bash
mkdir -p infrastructure/prompts/napoleon-framework
```

Create `infrastructure/prompts/napoleon-framework/v1.md` with content from `ACQUISITION_DEEP_RESEARCH_FORMAT.md` plus Bedrock instructions.

### Step 2: Upload to S3

```bash
# For staging
aws s3 cp infrastructure/prompts/napoleon-framework/v1.md \
  s3://bluemoxon-staging-images/prompts/napoleon-framework/v1.md

# For production
aws s3 cp infrastructure/prompts/napoleon-framework/v1.md \
  s3://bluemoxon-images/prompts/napoleon-framework/v1.md
```

### Step 3: Commit

```bash
git add infrastructure/prompts/
git commit -m "feat: add Napoleon framework prompt for Bedrock"
```

---

## Task 11: Add Bedrock Permissions to Lambda

**Files:**
- Modify: `infra/lib/backend-stack.ts` (or equivalent CDK/Terraform)

### Step 1: Add Bedrock permissions

Add to the Lambda execution role:

```typescript
// Bedrock permissions for analysis generation
lambdaRole.addToPolicy(
  new iam.PolicyStatement({
    effect: iam.Effect.ALLOW,
    actions: ["bedrock:InvokeModel"],
    resources: [
      "arn:aws:bedrock:*::foundation-model/anthropic.claude-sonnet-4-5-*",
      "arn:aws:bedrock:*::foundation-model/anthropic.claude-opus-4-5-*",
    ],
  })
);
```

### Step 2: Deploy infrastructure

```bash
cd infra && cdk deploy
```

### Step 3: Commit

```bash
git add infra/
git commit -m "feat: add Bedrock invoke permissions to Lambda role"
```

---

## Task 12: Verification and Manual Testing

### Step 1: Run all backend tests

```bash
cd backend && python -m pytest -v
```

Expected: All tests pass

### Step 2: Run all frontend tests

```bash
cd frontend && npm test -- --run
```

Expected: All tests pass

### Step 3: Run type check and build

```bash
cd frontend && npm run type-check && npm run build
```

Expected: No errors

### Step 4: Push to staging

```bash
git push origin staging
```

### Step 5: Manual test on staging

1. Navigate to https://staging.app.bluemoxon.com
2. Login as admin
3. Go to a book detail page
4. Open the Analysis viewer
5. Select model (Sonnet or Opus)
6. Click "Generate" or "Regenerate"
7. Wait 30-60 seconds
8. Verify analysis appears

### Step 6: Test from acquisitions dashboard

1. Go to /admin/acquisitions
2. Find an EVALUATING item
3. Click the Analysis button
4. Verify analysis generates

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Bedrock client and prompt loader | `services/bedrock.py` |
| 2 | Source URL fetcher | `services/bedrock.py` |
| 3 | Image fetcher for Bedrock | `services/bedrock.py` |
| 4 | Bedrock invoke function | `services/bedrock.py` |
| 5 | Generate analysis API endpoint | `api/v1/books.py` |
| 6 | Update conftest for admin mock | `tests/conftest.py` |
| 7 | Frontend store action | `stores/books.ts` |
| 8 | Generate button in AnalysisViewer | `AnalysisViewer.vue` |
| 9 | Generate button in AcquisitionsView | `AcquisitionsView.vue` |
| 10 | Upload Napoleon prompt to S3 | S3 upload |
| 11 | Add Bedrock permissions | CDK/Infrastructure |
| 12 | Verification and manual testing | - |

**Total: 12 tasks**
