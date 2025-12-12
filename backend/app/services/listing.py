"""eBay listing extraction and processing service."""

import json
import logging
import re
import unicodedata
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models import Author, Binder, Publisher
from app.services.bedrock import get_bedrock_client

logger = logging.getLogger(__name__)

EBAY_HOSTS = {"ebay.com", "www.ebay.com", "m.ebay.com"}
EBAY_ITEM_PATTERN = re.compile(r"/itm/(?:[^/]+/)?(\d+)")


def is_valid_ebay_url(url: str) -> bool:
    """Check if URL is a valid eBay listing URL."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host not in EBAY_HOSTS:
            return False
        return bool(EBAY_ITEM_PATTERN.search(parsed.path))
    except Exception:
        return False


def normalize_ebay_url(url: str) -> tuple[str, str]:
    """Normalize eBay URL and extract item ID.

    Returns:
        Tuple of (normalized_url, item_id)

    Raises:
        ValueError: If URL is not a valid eBay listing URL
    """
    if not is_valid_ebay_url(url):
        raise ValueError("Invalid eBay URL")

    parsed = urlparse(url)
    match = EBAY_ITEM_PATTERN.search(parsed.path)
    item_id = match.group(1)

    # Build canonical URL
    normalized = f"https://www.ebay.com/itm/{item_id}"
    return normalized, item_id


# =============================================================================
# Reference Matching (Authors, Publishers, Binders)
# =============================================================================


def normalize_name(name: str) -> str:
    """Normalize a name for matching."""
    # Normalize unicode and remove accents
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower()
    # Remove common suffixes
    name = re.sub(r"\s*&\s*(son|co\.?|sons|company)\s*", "", name)
    name = re.sub(r"\s*(ltd\.?|limited|inc\.?)\s*", "", name)
    # Remove punctuation
    name = re.sub(r"[^\w\s]", "", name)
    # Normalize whitespace
    name = " ".join(name.split())
    return name.strip()


def jaccard_similarity(s1: str, s2: str) -> float:
    """Calculate Jaccard similarity between two strings."""
    tokens1 = set(s1.split())
    tokens2 = set(s2.split())
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    return len(intersection) / len(union)


def match_reference(
    name: str,
    records: list[tuple[int, str]],  # List of (id, name) tuples
    threshold: float = 0.9,
) -> dict | None:
    """Match a name against records using fuzzy matching.

    Returns:
        Dict with id, name, similarity if match found, else None
    """
    normalized_input = normalize_name(name)
    best_match = None
    best_similarity = 0.0

    for record_id, record_name in records:
        normalized_record = normalize_name(record_name)

        # Exact match
        if normalized_input == normalized_record:
            return {"id": record_id, "name": record_name, "similarity": 1.0}

        # Fuzzy match
        similarity = jaccard_similarity(normalized_input, normalized_record)
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = {"id": record_id, "name": record_name, "similarity": similarity}

    if best_match and best_similarity >= threshold:
        return best_match
    return None


def match_author(name: str, db: Session, threshold: float = 0.9) -> dict | None:
    """Match author name against database."""
    authors = db.query(Author.id, Author.name).all()
    return match_reference(name, authors, threshold)


def match_publisher(name: str, db: Session, threshold: float = 0.9) -> dict | None:
    """Match publisher name against database."""
    publishers = db.query(Publisher.id, Publisher.name).all()
    return match_reference(name, publishers, threshold)


def match_binder(name: str, db: Session, threshold: float = 0.9) -> dict | None:
    """Match binder name against database."""
    binders = db.query(Binder.id, Binder.name).all()
    return match_reference(name, binders, threshold)


# =============================================================================
# Bedrock Listing Extraction
# =============================================================================

EXTRACTION_PROMPT = """Extract book listing details as JSON. Return ONLY valid JSON, no explanation.

{{
  "title": "book title only, no author/publisher in title",
  "author": "author name",
  "publisher": "publisher name if mentioned",
  "binder": "bindery name if mentioned (Rivière, Zaehnsdorf, Bayntun, etc.)",
  "price": 165.00,
  "currency": "USD or GBP or EUR",
  "publication_date": "year or date string",
  "volumes": 1,
  "condition": "condition notes",
  "binding": "binding description"
}}

Listing HTML:
{listing_html}"""


def invoke_bedrock_extraction(html: str) -> dict:
    """Invoke Bedrock Claude Haiku to extract structured data from listing HTML.

    Args:
        html: Raw HTML content from listing page (will be truncated if too long)

    Returns:
        Dict with extracted book data

    Raises:
        ValueError: If response cannot be parsed as JSON
    """
    client = get_bedrock_client()

    # Truncate HTML if too long (Bedrock has token limits)
    truncated_html = html[:50000]
    prompt = EXTRACTION_PROMPT.format(listing_html=truncated_html)

    response = client.invoke_model(
        modelId="anthropic.claude-3-haiku-20240307-v1:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            }
        ),
    )

    response_body = json.loads(response["body"].read())
    content = response_body["content"][0]["text"]

    # Parse JSON from response - handle markdown code blocks
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Bedrock response: {content}")
        raise ValueError(f"Failed to parse listing data: {e}") from e

    return data


def extract_listing_data(html: str) -> dict:
    """Extract structured book data from listing HTML using Bedrock Claude Haiku.

    High-level function that calls Bedrock and ensures defaults are set.

    Args:
        html: Raw HTML content from listing page

    Returns:
        Dict with extracted book data, with defaults for missing fields
    """
    data = invoke_bedrock_extraction(html)

    # Ensure required fields have defaults
    data.setdefault("volumes", 1)
    data.setdefault("currency", "USD")

    return data
