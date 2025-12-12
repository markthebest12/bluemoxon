"""eBay listing extraction and processing service."""

import re
import unicodedata
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models import Author, Binder, Publisher

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
