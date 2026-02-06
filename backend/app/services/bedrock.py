"""AWS Bedrock service for AI-powered analysis generation."""

import base64
import io
import json  # Used in invoke_bedrock() (Task 4)
import logging
import os
import random
import time
from functools import lru_cache, wraps

import boto3
import httpx
from botocore.exceptions import ClientError
from PIL import Image

from app.config import get_settings
from app.constants import DEFAULT_ANALYSIS_MODEL
from app.models import BookImage
from app.services.aws_clients import get_s3_client
from app.utils.image_utils import detect_content_type

# Bedrock error codes that warrant a retry (transient rate/availability issues).
# Omits ModelStreamErrorException (we don't use streaming) and InternalServerException
# (undocumented for invoke_model; would mask genuine bugs).
RETRYABLE_ERROR_CODES = frozenset(
    {
        "ThrottlingException",
        "TooManyRequestsException",
        "ServiceUnavailableException",
    }
)


def bedrock_retry(max_retries: int = 3, base_delay: float = 5.0):
    """Decorator that retries a function on transient Bedrock errors.

    Implements exponential backoff with jitter for errors whose code is
    in ``RETRYABLE_ERROR_CODES``.  Non-retryable ``ClientError`` exceptions
    are re-raised immediately.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds for exponential backoff.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_error: ClientError | None = None
            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        delay = base_delay * (2**attempt) + random.uniform(0, 1)  # noqa: S311
                        logger.info(
                            "Bedrock retry attempt %d/%d after %.1fs delay",
                            attempt,
                            max_retries,
                            delay,
                        )
                        time.sleep(delay)
                    return fn(*args, **kwargs)
                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "Unknown")
                    if error_code in RETRYABLE_ERROR_CODES and attempt < max_retries:
                        logger.warning(
                            "Bedrock %s (attempt %d/%d): %s",
                            error_code,
                            attempt + 1,
                            max_retries + 1,
                            e,
                        )
                        last_error = e
                        continue
                    raise
            # All retries exhausted (shouldn't normally reach here)
            raise last_error  # type: ignore[misc]

        return wrapper

    return decorator


# Claude's maximum image size limit (base64 encoded) is 5MB
# Base64 adds ~33% overhead, so raw limit is ~3.75MB
CLAUDE_MAX_IMAGE_BYTES = 5_242_880  # 5MB in bytes
CLAUDE_SAFE_RAW_BYTES = 3_500_000  # Leave margin for base64 overhead

logger = logging.getLogger(__name__)
settings = get_settings()

# Model ID mapping - use inference profile IDs for Claude models
# Claude 4.5 Sonnet tested working 2025-12-12 (~23s for Napoleon analysis)
# GitHub #178 resolved - was provisioning delay after Marketplace approval
# NOTE: These IDs must match infra/terraform/locals.tf:bedrock_model_ids for IAM access
MODEL_IDS = {
    "sonnet": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",  # Claude 4.5 Sonnet
    "opus": "us.anthropic.claude-opus-4-6-v1",  # Claude Opus 4.6
    "haiku": "anthropic.claude-3-5-haiku-20241022-v1:0",  # Claude 3.5 Haiku
}

# Model usage descriptions for admin dashboard
MODEL_USAGE = {
    "sonnet": "Eval runbooks, FMV lookup, Listing extraction, Napoleon analysis (optional)",
    "opus": "Napoleon analysis (default)",
    "haiku": "Entity profiles",
}

# Prompt cache with TTL
_prompt_cache: dict = {"prompt": None, "timestamp": 0}
PROMPT_CACHE_TTL = 300  # 5 minutes

# S3 prompt location
PROMPTS_BUCKET = os.environ.get("PROMPTS_BUCKET", settings.images_bucket)
PROMPT_KEY = "prompts/napoleon-framework/v3.md"

# Processed image note for AI prompts
PROCESSED_IMAGE_NOTE = """Note: This image has had its background digitally removed and replaced with a solid color. Disregard any edge artifacts, halos, or unnatural boundaries - focus your analysis on the book itself."""

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


@lru_cache(maxsize=1)
def get_bedrock_client():
    """Get cached Bedrock runtime client with extended timeout for long generations."""
    from botocore.config import Config

    region = os.environ.get("AWS_REGION", settings.aws_region)
    # Extended read timeout for long Claude responses (default is 60s)
    config = Config(read_timeout=540, connect_timeout=10, retries={"max_attempts": 0})
    return boto3.client("bedrock-runtime", region_name=region, config=config)


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
            response = client.get(
                url, headers={"User-Agent": "Mozilla/5.0 (compatible; BlueMoxon/1.0)"}
            )
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


def resize_image_for_bedrock(image_data: bytes, media_type: str) -> tuple[bytes, str]:
    """Resize image if it would exceed Claude's base64 size limit.

    Claude has a 5MB limit per base64-encoded image. This function checks if
    the image would exceed that limit and progressively resizes it until it fits.

    Args:
        image_data: Raw image bytes
        media_type: MIME type (e.g., "image/jpeg")

    Returns:
        Tuple of (possibly resized image bytes, media type)
    """
    # Check if resize is needed (base64 adds ~33% overhead)
    if len(image_data) <= CLAUDE_SAFE_RAW_BYTES:
        return image_data, media_type

    logger.info(f"Image size {len(image_data):,} bytes exceeds safe limit, resizing...")

    try:
        img = Image.open(io.BytesIO(image_data))
        original_size = img.size

        # Convert to RGB if needed (RGBA, palette modes can't save as JPEG)
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        # Progressively reduce size until it fits
        scale = 0.9
        output_format = "JPEG"
        output_media_type = "image/jpeg"

        for _ in range(10):  # Max 10 resize attempts
            new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
            resized = img.resize(new_size, Image.Resampling.LANCZOS)

            # Save to bytes with quality optimization
            buffer = io.BytesIO()
            resized.save(buffer, format=output_format, quality=85, optimize=True)
            resized_data = buffer.getvalue()

            if len(resized_data) <= CLAUDE_SAFE_RAW_BYTES:
                logger.info(
                    f"Resized image from {original_size} to {new_size}, "
                    f"size reduced from {len(image_data):,} to {len(resized_data):,} bytes"
                )
                return resized_data, output_media_type

            scale *= 0.8  # More aggressive reduction each iteration

        # If still too large after max attempts, return last attempt
        logger.warning(
            f"Could not resize image below limit after max attempts, "
            f"using {len(resized_data):,} bytes"
        )
        return resized_data, output_media_type

    except Exception as e:
        logger.warning(f"Failed to resize image: {e}, using original")
        return image_data, media_type


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
    max_images: int = 20,
) -> list[dict]:
    """Fetch book images from S3 and format for Bedrock.

    Uses a selection algorithm that takes first ~67% and last ~33% of images
    by display_order. This catches both main book content and any seller
    promotional images at the end. Default of 20 images ensures middle
    content (like provenance markers on endpapers) isn't skipped.

    Note: Eval runbook removes advertisement images before this runs,
    so increasing max_images won't waste tokens on ads.

    Args:
        images: List of BookImage objects
        max_images: Maximum number of images to include (default 20)

    Returns:
        List of Bedrock-formatted image content blocks
    """
    if not images:
        return []

    result = []
    s3 = get_s3_client()
    bucket = settings.images_bucket

    # Sort by display_order
    sorted_images = sorted(images, key=lambda x: x.display_order)

    # Take first AND last images to catch seller ads at end of listings
    # Seller promotional images tend to be at the end, so we need both
    if len(sorted_images) <= max_images:
        selected_images = sorted_images
    else:
        # Split: take first portion and last portion
        first_count = max_images - (max_images // 3)  # ~67% from start
        last_count = max_images // 3  # ~33% from end
        first_images = sorted_images[:first_count]
        last_images = sorted_images[-last_count:]
        # Combine and dedupe (in case of overlap)
        selected_indices = {img.display_order for img in first_images}
        selected_images = list(first_images)
        for img in last_images:
            if img.display_order not in selected_indices:
                selected_images.append(img)
        # Re-sort by display_order for consistent output
        selected_images = sorted(selected_images, key=lambda x: x.display_order)

    for img in selected_images:
        try:
            # Fetch from S3
            s3_key = f"books/{img.s3_key}"
            response = s3.get_object(Bucket=bucket, Key=s3_key)
            image_data = response["Body"].read()

            # Detect actual format from image content (more reliable than S3 metadata)
            content_type = detect_content_type(image_data[:12])

            # Resize if needed to fit Claude's 5MB base64 limit
            image_data, content_type = resize_image_for_bedrock(image_data, content_type)

            result.append(format_image_for_bedrock(image_data, content_type))
            logger.debug(f"Loaded image {img.s3_key} for Bedrock")

        except Exception as e:
            logger.warning(f"Failed to load image {img.s3_key}: {e}")
            continue

    logger.info(f"Loaded {len(result)} images for Bedrock analysis")
    return result


def build_bedrock_messages(
    book_data: dict,
    images: list[dict],
    source_content: str | None,
    primary_image_processed: bool = False,
) -> list[dict]:
    """Build messages array for Bedrock Claude API.

    Args:
        book_data: Dict with book metadata
        images: List of Bedrock-formatted image blocks
        source_content: Optional HTML content from source URL
        primary_image_processed: Whether primary image had background removed

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
        binder_line = f"- Binder: {book_data['binder']}"
        if book_data.get("binder_tier"):
            binder_line += f" (Tier: {book_data['binder_tier']})"
        text_parts.append(binder_line)
        if book_data.get("binder_authentication_markers"):
            text_parts.append(
                f"- Authentication Markers: {book_data['binder_authentication_markers']}"
            )
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

        if primary_image_processed:
            text_parts.append(f"\n{PROCESSED_IMAGE_NOTE}")

    user_text = "\n".join(text_parts)

    # Build content array with text first, then images
    content = [{"type": "text", "text": user_text}]
    content.extend(images)

    return [{"role": "user", "content": content}]


def invoke_bedrock(
    messages: list[dict],
    model: str = DEFAULT_ANALYSIS_MODEL,
    max_tokens: int = 32000,
    max_retries: int = 3,
    base_delay: float = 5.0,
) -> str:
    """Invoke Bedrock Claude model and return response text.

    Implements exponential backoff retry for throttling errors (tokens per minute limits).

    Args:
        messages: Messages array for Claude
        model: Model name ("sonnet" or "opus")
        max_tokens: Maximum tokens in response
        max_retries: Maximum number of retry attempts (default 3)
        base_delay: Base delay in seconds for exponential backoff (default 5.0)

    Returns:
        Generated text response

    Raises:
        Exception: If Bedrock invocation fails after all retries
    """
    client = get_bedrock_client()
    model_id = get_model_id(model)
    system_prompt = load_napoleon_prompt()

    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": messages,
        }
    )

    @bedrock_retry(max_retries=max_retries, base_delay=base_delay)
    def _call():
        logger.info(f"Invoking Bedrock model {model_id}")

        response = client.invoke_model(
            modelId=model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        stop_reason = response_body.get("stop_reason", "unknown")
        result_text = response_body["content"][0]["text"]

        logger.info(f"Bedrock returned {len(result_text)} chars, stop_reason={stop_reason}")
        if stop_reason == "max_tokens":
            logger.warning("Output truncated - hit max_tokens limit")
        return result_text

    return _call()


# ============================================================================
# Two-Stage Extraction (Stage 2)
# ============================================================================

# Extraction prompt configuration
EXTRACTION_PROMPT_KEY = "prompts/extraction/structured-data.md"
_extraction_prompt_cache: dict = {"prompt": None, "timestamp": 0}

# Fallback extraction prompt if S3 unavailable
FALLBACK_EXTRACTION_PROMPT = """Extract structured data from the analysis. Output ONLY valid JSON:
{
  "condition_grade": "Fine|VG+|VG|VG-|Good+|Good|Fair|Poor or null",
  "binder_identified": "name or null",
  "binder_confidence": "HIGH|MEDIUM|LOW|NONE",
  "binding_type": "type or null",
  "valuation_low": number,
  "valuation_mid": number,
  "valuation_high": number,
  "era_period": "Victorian|Romantic|Georgian|Edwardian|Modern or null",
  "publication_year": number or null,
  "is_first_edition": true|false|null,
  "has_provenance": true|false,
  "provenance_tier": "Tier 1|Tier 2|Tier 3" or null
}"""


def load_extraction_prompt() -> str:
    """Load extraction prompt from S3 with caching."""
    global _extraction_prompt_cache

    current_time = time.time()

    if (
        _extraction_prompt_cache["prompt"]
        and (current_time - _extraction_prompt_cache["timestamp"]) < PROMPT_CACHE_TTL
    ):
        logger.debug("Using cached extraction prompt")
        return _extraction_prompt_cache["prompt"]

    try:
        s3 = get_s3_client()
        response = s3.get_object(Bucket=PROMPTS_BUCKET, Key=EXTRACTION_PROMPT_KEY)
        prompt = response["Body"].read().decode("utf-8")
        logger.info(f"Loaded extraction prompt from s3://{PROMPTS_BUCKET}/{EXTRACTION_PROMPT_KEY}")
        _extraction_prompt_cache = {"prompt": prompt, "timestamp": current_time}
        return prompt

    except Exception as e:
        logger.warning(f"Failed to load extraction prompt: {e}")
        return FALLBACK_EXTRACTION_PROMPT


def extract_structured_data(
    analysis_text: str | None,
    model: str = DEFAULT_ANALYSIS_MODEL,
    max_retries: int = 3,
    base_delay: float = 2.0,
) -> dict | None:
    """Extract structured data from analysis using a focused Bedrock call.

    Stage 2 of two-stage approach: takes completed analysis and extracts
    machine-readable values via a separate, focused prompt.

    Implements exponential backoff retry for throttling errors (tokens per minute limits).

    Args:
        analysis_text: The full analysis markdown text
        model: Model to use (default sonnet for speed)
        max_retries: Maximum number of retry attempts (default 3)
        base_delay: Base delay in seconds for exponential backoff (default 2.0)

    Returns:
        Dict with extracted values, or None if extraction fails
    """
    if not analysis_text:
        return None

    client = get_bedrock_client()
    model_id = get_model_id(model)
    extraction_prompt = load_extraction_prompt()

    # Build simple message with analysis appended
    user_message = f"{extraction_prompt}\n\n{analysis_text}\n```"

    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,  # JSON output is small
            "messages": [{"role": "user", "content": user_message}],
        }
    )

    @bedrock_retry(max_retries=max_retries, base_delay=base_delay)
    def _call():
        logger.info("Invoking Bedrock for structured data extraction")

        response = client.invoke_model(
            modelId=model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        result_text = response_body["content"][0]["text"].strip()

        # Parse JSON from response (handle potential markdown code blocks)
        json_text = result_text
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0]
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0]

        extracted = json.loads(json_text.strip())
        logger.info(f"Extracted structured data: {list(extracted.keys())}")
        return extracted

    try:
        return _call()
    except ClientError as e:
        logger.error("Bedrock ClientError: %s", e)
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse extraction JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return None
