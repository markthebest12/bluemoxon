"""eBay listing extraction and processing service."""

import re
from urllib.parse import urlparse

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
