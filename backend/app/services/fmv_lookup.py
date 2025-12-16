"""Fair Market Value lookup service for eBay and AbeBooks comparables.

Uses web search and Claude extraction to find comparable sold listings.
"""

import json
import logging
import re
import urllib.parse

import httpx

from app.services.bedrock import get_bedrock_client, get_model_id

logger = logging.getLogger(__name__)

# Search URL templates
EBAY_SOLD_SEARCH_URL = (
    "https://www.ebay.com/sch/i.html?"
    "_nkw={query}&"
    "_sacat=267&"  # Books category
    "LH_Complete=1&"  # Completed listings
    "LH_Sold=1&"  # Sold items only
    "_sop=13"  # Sort by price + shipping: highest first
)

ABEBOOKS_SEARCH_URL = (
    "https://www.abebooks.com/servlet/SearchResults?"
    "kn={query}&"
    "sortby=17"  # Sort by price descending
)


def _build_search_query(title: str, author: str | None = None) -> str:
    """Build a search query from book metadata.

    Args:
        title: Book title
        author: Optional author name

    Returns:
        URL-encoded search query
    """
    # Clean title - remove common noise words that hurt search
    title_clean = re.sub(r"\b(the|a|an|and|or|of|in|to|for)\b", " ", title.lower())
    title_clean = re.sub(r"[^\w\s]", " ", title_clean)  # Remove punctuation
    title_clean = " ".join(title_clean.split()[:6])  # Take first 6 words

    query_parts = [title_clean]
    if author:
        # Take just last name for better matches
        author_parts = author.split()
        if author_parts:
            query_parts.append(author_parts[-1])

    query = " ".join(query_parts)
    return urllib.parse.quote_plus(query)


def _fetch_search_page(url: str, timeout: int = 45) -> str | None:
    """Fetch search results page HTML.

    Args:
        url: Search URL
        timeout: Request timeout

    Returns:
        HTML content or None if failed
    """
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            response.raise_for_status()

            # Truncate to reasonable size for Claude
            content = response.text
            max_chars = 100000  # ~25k tokens
            if len(content) > max_chars:
                content = content[:max_chars]

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


def _extract_comparables_with_claude(
    html: str,
    source: str,
    book_title: str,
    max_results: int = 5,
) -> list[dict]:
    """Use Claude to extract comparable listings from search results HTML.

    Args:
        html: Search results HTML
        source: Source name ("ebay" or "abebooks")
        book_title: Original book title for relevance filtering
        max_results: Maximum comparables to return

    Returns:
        List of comparable dicts with title, price, url, condition, sold_date
    """
    prompt = f"""Extract the top {max_results} most relevant sold book listings from this {source} search results page.

The book being evaluated is: "{book_title}"

Only include listings that appear to be the SAME book or very similar editions.
Skip listings that are clearly different books.

For each relevant listing, extract:
- title: The listing title
- price: Sale price in USD (number only, no currency symbol)
- url: Full URL to the listing (if available)
- condition: Condition description if stated
- sold_date: When it sold (if available, format: YYYY-MM-DD or "recent" if not specific)
- relevance: "high", "medium", or "low" based on how closely it matches the target book

Return JSON array only, no other text:
[
  {{"title": "...", "price": 150.00, "url": "...", "condition": "...", "sold_date": "...", "relevance": "high"}},
  ...
]

If no relevant listings found, return empty array: []

HTML CONTENT:
{html[:80000]}
"""

    try:
        client = get_bedrock_client()
        model_id = get_model_id("sonnet")

        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}],
            }
        )

        response = client.invoke_model(
            modelId=model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        result_text = response_body["content"][0]["text"]

        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r"\[[\s\S]*\]", result_text)
        if json_match:
            comparables = json.loads(json_match.group())
            # Filter to high/medium relevance only
            return [c for c in comparables if c.get("relevance") in ("high", "medium")][
                :max_results
            ]

        return []

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse Claude response as JSON: {e}")
        return []
    except Exception as e:
        logger.error(f"Claude extraction failed: {e}")
        return []


def lookup_ebay_comparables(
    title: str,
    author: str | None = None,
    max_results: int = 5,
) -> list[dict]:
    """Look up comparable sold listings on eBay.

    Args:
        title: Book title
        author: Optional author name
        max_results: Maximum comparables to return

    Returns:
        List of comparable dicts with title, price, url, condition, sold_date
    """
    query = _build_search_query(title, author)
    url = EBAY_SOLD_SEARCH_URL.format(query=query)

    logger.info(f"Searching eBay sold listings: {url}")
    html = _fetch_search_page(url)

    if not html:
        logger.warning("Failed to fetch eBay search results")
        return []

    comparables = _extract_comparables_with_claude(html, "ebay", title, max_results)
    logger.info(f"Found {len(comparables)} eBay comparables")
    return comparables


def lookup_abebooks_comparables(
    title: str,
    author: str | None = None,
    max_results: int = 5,
) -> list[dict]:
    """Look up comparable listings on AbeBooks.

    Args:
        title: Book title
        author: Optional author name
        max_results: Maximum comparables to return

    Returns:
        List of comparable dicts with title, price, url, condition
    """
    query = _build_search_query(title, author)
    url = ABEBOOKS_SEARCH_URL.format(query=query)

    logger.info(f"Searching AbeBooks: {url}")
    html = _fetch_search_page(url)

    if not html:
        logger.warning("Failed to fetch AbeBooks search results")
        return []

    comparables = _extract_comparables_with_claude(html, "abebooks", title, max_results)
    logger.info(f"Found {len(comparables)} AbeBooks comparables")
    return comparables


def lookup_fmv(
    title: str,
    author: str | None = None,
    max_per_source: int = 5,
) -> dict:
    """Look up Fair Market Value from multiple sources.

    Args:
        title: Book title
        author: Optional author name
        max_per_source: Maximum comparables per source

    Returns:
        Dict with:
            - ebay_comparables: List of eBay sold listings
            - abebooks_comparables: List of AbeBooks listings
            - fmv_low: Low estimate based on comparables
            - fmv_high: High estimate based on comparables
            - fmv_notes: Summary of FMV analysis
    """
    ebay = lookup_ebay_comparables(title, author, max_per_source)
    abebooks = lookup_abebooks_comparables(title, author, max_per_source)

    # Calculate FMV range from comparables
    all_prices = []
    for comp in ebay + abebooks:
        if comp.get("price") and isinstance(comp["price"], (int, float)):
            all_prices.append(float(comp["price"]))

    fmv_low = None
    fmv_high = None
    fmv_notes = ""

    if all_prices:
        all_prices.sort()
        # Use 25th and 75th percentile for range
        n = len(all_prices)
        fmv_low = all_prices[max(0, n // 4)]
        fmv_high = all_prices[min(n - 1, 3 * n // 4)]
        fmv_notes = f"Based on {len(ebay)} eBay sold and {len(abebooks)} AbeBooks listings"
    else:
        fmv_notes = "No comparable listings found"

    return {
        "ebay_comparables": ebay,
        "abebooks_comparables": abebooks,
        "fmv_low": fmv_low,
        "fmv_high": fmv_high,
        "fmv_notes": fmv_notes,
    }
