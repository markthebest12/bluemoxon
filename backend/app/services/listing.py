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

EBAY_HOSTS = {"ebay.com", "www.ebay.com", "m.ebay.com", "ebay.us", "www.ebay.us"}
EBAY_ITEM_PATTERN = re.compile(r"/itm/(?:[^/]+/)?(\d+)")


def is_valid_ebay_url(url: str) -> bool:
    """Check if URL is a valid eBay listing URL."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host not in EBAY_HOSTS:
            return False

        # ebay.us short URLs don't have /itm/ pattern - they redirect to full URLs
        if "ebay.us" in host:
            # Accept any ebay.us URL with a path (e.g., /m/9R8Zfd)
            return bool(parsed.path and len(parsed.path) > 1)

        # Standard eBay URLs must have /itm/ pattern
        return bool(EBAY_ITEM_PATTERN.search(parsed.path))
    except Exception:
        return False


def normalize_ebay_url(url: str) -> tuple[str, str]:
    """Normalize eBay URL and extract item ID.

    For ebay.us short URLs, follows the redirect to get the canonical URL.

    Returns:
        Tuple of (normalized_url, item_id)

    Raises:
        ValueError: If URL is not a valid eBay listing URL
    """
    if not is_valid_ebay_url(url):
        raise ValueError("Invalid eBay URL")

    parsed = urlparse(url)

    # Handle ebay.us short URLs - follow redirect to get real item ID
    if "ebay.us" in parsed.netloc.lower():
        try:
            import httpx

            # Follow redirects to get final URL
            # NOTE: Must use GET not HEAD - eBay short URLs don't handle HEAD properly
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            with httpx.Client(
                follow_redirects=True, timeout=15.0, max_redirects=10, headers=headers
            ) as client:
                response = client.get(url)
                final_url = str(response.url)
                logger.info(f"Resolved ebay.us short URL: {url} -> {final_url}")

            # Check if eBay returned an error page (expired/invalid short URL)
            if "/n/error" in final_url or "page_not_responding" in final_url:
                raise ValueError(
                    "Short URL has expired or is invalid. Please use the full eBay listing URL."
                )

            # Extract item_id from final URL
            match = EBAY_ITEM_PATTERN.search(final_url)
            if not match:
                raise ValueError(f"Could not extract item ID from redirected URL: {final_url}")
            item_id = match.group(1)
        except httpx.TooManyRedirects:
            logger.error(f"Too many redirects for ebay.us short URL {url}")
            raise ValueError(
                "Short URL has expired or is invalid. Please use the full eBay listing URL."
            ) from None
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to resolve ebay.us short URL {url}: {e}")
            raise ValueError(f"Failed to resolve short URL: {e}") from e
    else:
        # Standard eBay URL - extract item_id directly
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
    # Remove parenthetical content (birth/death dates, etc.)
    name = re.sub(r"\s*\([^)]*\)\s*", " ", name)
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


def match_author(name: str, db: Session, threshold: float = 0.7) -> dict | None:
    """Match author name against database."""
    authors = db.query(Author.id, Author.name).all()
    return match_reference(name, authors, threshold)


def match_publisher(name: str, db: Session, threshold: float = 0.7) -> dict | None:
    """Match publisher name against database."""
    publishers = db.query(Publisher.id, Publisher.name).all()
    return match_reference(name, publishers, threshold)


def match_binder(name: str, db: Session, threshold: float = 0.7) -> dict | None:
    """Match binder name against database."""
    binders = db.query(Binder.id, Binder.name).all()
    return match_reference(name, binders, threshold)


# =============================================================================
# Bedrock Listing Extraction
# =============================================================================

EXTRACTION_PROMPT = """Extract book listing details as JSON. Return ONLY valid JSON, no explanation.

{{
  "title": "book title only, no author/publisher/binder in title",
  "author": "author name only, no dates (e.g., 'John Ruskin' not 'John Ruskin (1819-1900)')",
  "publisher": "original publisher name if mentioned (e.g., 'Chapman & Hall', 'Macmillan')",
  "binder": "bindery/bookbinder name if mentioned (Rivière, Zaehnsdorf, Bayntun, Sangorski)",
  "price": 165.00,
  "currency": "USD or GBP or EUR",
  "publication_date": "year or date string",
  "volumes": 1,
  "condition": "condition notes",
  "binding_type": "binding material and coverage ONLY (e.g., 'Full calf', 'Half morocco', 'Full morocco', 'Quarter leather', 'Tree calf', 'Vellum', 'Cloth')"
}}

Listing HTML:
{listing_html}"""


def extract_relevant_html(html: str) -> str:
    """Extract relevant content from eBay HTML for Bedrock processing.

    Modern eBay pages have listing data buried deep in the HTML (500KB+).
    This function extracts the key content: meta tags, title, price info.
    """
    parts = []

    # Extract title tag
    title_match = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
    if title_match:
        parts.append(f"Page Title: {title_match.group(1)}")

    # Extract meta description (contains detailed listing info)
    desc_match = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html, re.IGNORECASE)
    if desc_match:
        parts.append(f"Description: {desc_match.group(1)}")

    # Extract Open Graph description (often same but sometimes different)
    og_desc_match = re.search(
        r'<meta\s+property="og:description"\s+content="([^"]+)"', html, re.IGNORECASE
    )
    if og_desc_match and og_desc_match.group(1) != (desc_match.group(1) if desc_match else ""):
        parts.append(f"OG Description: {og_desc_match.group(1)}")

    # Extract price if visible in HTML (look for common patterns)
    price_patterns = [
        r'"price":\s*"?([0-9,.]+)"?',
        r'itemprop="price"\s+content="([0-9,.]+)"',
        r'class="[^"]*price[^"]*"[^>]*>([^<]*\$[0-9,.]+[^<]*)<',
    ]
    for pattern in price_patterns:
        price_match = re.search(pattern, html, re.IGNORECASE)
        if price_match:
            parts.append(f"Price: {price_match.group(1)}")
            break

    # If we found meta tags, use them; otherwise fall back to truncation
    if parts:
        return "\n".join(parts)

    # Fallback: return truncated HTML
    return html[:50000]


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

    # Extract relevant content from potentially huge eBay HTML
    relevant_content = extract_relevant_html(html)
    logger.info(f"Extracted {len(relevant_content)} chars from {len(html)} char HTML")
    prompt = EXTRACTION_PROMPT.format(listing_html=relevant_content)

    response = client.invoke_model(
        modelId="anthropic.claude-3-5-haiku-20241022-v1:0",
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

    # Normalize binding field name (binding_type -> binding for API compatibility)
    if "binding_type" in data and "binding" not in data:
        data["binding"] = data.pop("binding_type")

    return data
