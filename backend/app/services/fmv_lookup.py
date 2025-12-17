"""Fair Market Value lookup service for eBay and AbeBooks comparables.

Uses web search and Claude extraction to find comparable sold listings.
eBay requests use the scraper Lambda with Playwright for bot detection avoidance.
"""

import json
import logging
import os
import re
import urllib.parse

import httpx

from app.services.bedrock import get_bedrock_client, get_model_id

logger = logging.getLogger(__name__)

# Scraper Lambda function name pattern
SCRAPER_FUNCTION_NAME = "bluemoxon-{environment}-scraper"

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


def _get_lambda_client():
    """Get boto3 Lambda client."""
    import boto3

    return boto3.client("lambda")


def _fetch_via_scraper_lambda(url: str) -> str | None:
    """Fetch URL via scraper Lambda (Playwright browser).

    Uses the scraper Lambda which runs a headless Chromium browser to avoid
    bot detection. This is required for eBay which blocks simple HTTP requests.

    Args:
        url: URL to fetch

    Returns:
        HTML content or None if failed
    """
    try:
        client = _get_lambda_client()
        environment = os.getenv("BMX_ENVIRONMENT", "staging")
        function_name = SCRAPER_FUNCTION_NAME.format(environment=environment)

        # fetch_images=False since we only need HTML for search results
        payload = {"url": url, "fetch_images": False}

        logger.info(f"Invoking scraper Lambda for FMV lookup: {url}")
        response = client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )

        # Check for Lambda execution error
        if response.get("FunctionError"):
            error_payload = json.loads(response["Payload"].read())
            error_msg = error_payload.get("errorMessage", "Unknown error")
            logger.error(f"Scraper Lambda execution failed: {error_msg}")
            return None

        # Parse Lambda response
        result = json.loads(response["Payload"].read())
        status_code = result.get("statusCode", 500)
        body = json.loads(result.get("body", "{}"))

        if status_code == 429:
            logger.warning("Rate limited by eBay via scraper Lambda")
            return None

        if status_code >= 400:
            error_msg = body.get("error", "Scraping failed")
            logger.error(f"Scraper Lambda error: {error_msg}")
            return None

        html = body.get("html", "")
        logger.info(f"Scraper Lambda returned {len(html)} chars of HTML")

        # Truncate to reasonable size for Claude
        max_chars = 100000  # ~25k tokens
        if len(html) > max_chars:
            html = html[:max_chars]

        return html

    except Exception as e:
        logger.error(f"Error invoking scraper Lambda: {e}")
        return None


def _fetch_listings_via_scraper_lambda(url: str) -> list[dict] | None:
    """Fetch and extract listings via scraper Lambda (Playwright browser).

    Uses the scraper Lambda's extract_listings mode which extracts structured
    listing data directly via JavaScript in the browser. This avoids the
    truncation issue where raw HTML was too large for Claude processing.

    Args:
        url: eBay search results URL

    Returns:
        List of listing dicts or None if failed
    """
    try:
        client = _get_lambda_client()
        environment = os.getenv("BMX_ENVIRONMENT", "staging")
        function_name = SCRAPER_FUNCTION_NAME.format(environment=environment)

        # Use extract_listings mode to get structured data directly
        payload = {"url": url, "fetch_images": False, "extract_listings": True}

        logger.info(f"Invoking scraper Lambda for listing extraction: {url}")
        response = client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )

        # Check for Lambda execution error
        if response.get("FunctionError"):
            error_payload = json.loads(response["Payload"].read())
            error_msg = error_payload.get("errorMessage", "Unknown error")
            logger.error(f"Scraper Lambda execution failed: {error_msg}")
            return None

        # Parse Lambda response
        result = json.loads(response["Payload"].read())
        status_code = result.get("statusCode", 500)
        body = json.loads(result.get("body", "{}"))

        if status_code == 429:
            logger.warning("Rate limited by eBay via scraper Lambda")
            return None

        if status_code >= 400:
            error_msg = body.get("error", "Scraping failed")
            logger.error(f"Scraper Lambda error: {error_msg}")
            return None

        listings = body.get("listings", [])
        listing_count = body.get("listing_count", len(listings))
        html_size = body.get("html_size", 0)

        logger.info(
            f"Scraper Lambda extracted {listing_count} listings from {html_size} chars of HTML"
        )

        return listings

    except Exception as e:
        logger.error(f"Error invoking scraper Lambda for listing extraction: {e}")
        return None


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


def _build_context_aware_query(
    title: str,
    author: str | None = None,
    volumes: int = 1,
    binding_type: str | None = None,
    binder: str | None = None,
    edition: str | None = None,
) -> str:
    """Build a context-aware search query from book metadata.

    Args:
        title: Book title
        author: Author name
        volumes: Number of volumes (adds "N volumes" if > 1)
        binding_type: Binding type (adds "morocco", "calf", etc.)
        binder: Binder name (adds binder name)
        edition: Edition info (adds "first edition" if contains "first")

    Returns:
        URL-encoded search query with context
    """
    # Clean title - remove common noise words
    title_clean = re.sub(r"\b(the|a|an|and|or|of|in|to|for)\b", " ", title.lower())
    title_clean = re.sub(r"[^\w\s]", " ", title_clean)
    title_words = title_clean.split()[:5]  # First 5 significant words

    query_parts = title_words

    # Add author last name
    if author:
        author_parts = author.split()
        if author_parts:
            query_parts.append(author_parts[-1].lower())

    # Add volume count for multi-volume sets
    if volumes > 1:
        query_parts.append(f"{volumes} volumes")

    # Add binding type keywords
    if binding_type:
        binding_lower = binding_type.lower()
        if "morocco" in binding_lower:
            query_parts.append("morocco")
        elif "calf" in binding_lower:
            query_parts.append("calf")
        elif "vellum" in binding_lower:
            query_parts.append("vellum")

    # Add binder name
    if binder:
        query_parts.append(binder.lower())

    # Add edition info
    if edition and "first" in edition.lower():
        query_parts.append("first edition")

    query = " ".join(query_parts)
    return urllib.parse.quote_plus(query)


def _filter_listings_with_claude(
    listings: list[dict],
    book_metadata: dict,
) -> list[dict]:
    """Filter listings by relevance using Claude.

    Args:
        listings: Raw listings from scraper
        book_metadata: Target book metadata for comparison

    Returns:
        Filtered listings with relevance scores (high/medium only)
    """
    if not listings:
        return []

    # Build metadata summary for prompt
    meta_parts = [f"Title: {book_metadata.get('title', 'Unknown')}"]
    if book_metadata.get("author"):
        meta_parts.append(f"Author: {book_metadata['author']}")
    if book_metadata.get("volumes", 1) > 1:
        meta_parts.append(f"Volumes: {book_metadata['volumes']}")
    if book_metadata.get("binding_type"):
        meta_parts.append(f"Binding: {book_metadata['binding_type']}")
    if book_metadata.get("binder"):
        meta_parts.append(f"Binder: {book_metadata['binder']}")
    if book_metadata.get("edition"):
        meta_parts.append(f"Edition: {book_metadata['edition']}")

    metadata_str = "\n".join(meta_parts)
    listings_json = json.dumps(listings, indent=2)

    prompt = f"""Target book:
{metadata_str}

Extracted listings:
{listings_json}

Task: Rate each listing's relevance to the target book as "high", "medium", or "low":
- HIGH: Same work, matching volume count (within 1), similar binding quality
- MEDIUM: Same work, different format (e.g., fewer volumes, lesser binding)
- LOW: Different work entirely, or single volume from a multi-volume set

Return a JSON array with all listings, adding a "relevance" field to each.
Only include listings rated "high" or "medium" in your response.
Return ONLY the JSON array, no other text."""

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

        # Extract JSON from response
        json_match = re.search(r"\[[\s\S]*\]", result_text)
        if json_match:
            filtered = json.loads(json_match.group())
            # Ensure only high/medium returned
            return [item for item in filtered if item.get("relevance") in ("high", "medium")]

        logger.warning("No JSON array found in Claude filtering response")
        return []

    except Exception as e:
        logger.error(f"Claude filtering failed: {e}")
        # Fall back to returning all listings with medium relevance
        return [{"relevance": "medium", **item} for item in listings]


def _fetch_search_page(url: str, timeout: int = 45, use_scraper_lambda: bool = False) -> str | None:
    """Fetch search results page HTML.

    Args:
        url: Search URL
        timeout: Request timeout (only used for direct HTTP requests)
        use_scraper_lambda: If True, use scraper Lambda with Playwright browser
                           (required for eBay to avoid bot detection)

    Returns:
        HTML content or None if failed
    """
    # Use scraper Lambda for eBay to avoid bot detection (HTTP 503)
    if use_scraper_lambda:
        return _fetch_via_scraper_lambda(url)

    # Direct HTTP request for other sites (AbeBooks, etc.)
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
    logger.info(
        f"Extracting {source} comparables: HTML size={len(html)} chars, title='{book_title}'"
    )

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

        logger.info(f"Claude {source} extraction raw response: {result_text[:500]}")

        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r"\[[\s\S]*\]", result_text)
        if json_match:
            comparables = json.loads(json_match.group())
            logger.info(f"Claude found {len(comparables)} total {source} listings")

            # Log relevance breakdown
            relevance_counts = {}
            for c in comparables:
                rel = c.get("relevance", "unknown")
                relevance_counts[rel] = relevance_counts.get(rel, 0) + 1
            logger.info(f"Relevance breakdown: {relevance_counts}")

            # Filter to high/medium relevance only
            filtered = [c for c in comparables if c.get("relevance") in ("high", "medium")][
                :max_results
            ]
            logger.info(f"After relevance filtering: {len(filtered)} {source} comparables")
            return filtered

        logger.warning(f"No JSON array found in Claude response for {source}")
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

    Uses scraper Lambda with Playwright browser to avoid eBay bot detection.
    The scraper extracts listings directly via JavaScript, avoiding the
    truncation issue where raw HTML was too large for processing.

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

    # Use extract_listings mode for direct structured data extraction
    listings = _fetch_listings_via_scraper_lambda(url)

    if listings is None:
        logger.warning("Failed to fetch eBay search results via scraper")
        return []

    if not listings:
        logger.info("No eBay listings found in search results")
        return []

    logger.info(f"Scraper returned {len(listings)} raw eBay listings")

    # Filter listings with valid prices and mark as sold
    valid_listings = []
    for listing in listings:
        # Skip listings without prices
        if not listing.get("price"):
            continue

        # Add default relevance (all are from search results matching query)
        listing["relevance"] = "medium"

        # Ensure sold_date has a value
        if not listing.get("sold_date"):
            listing["sold_date"] = "recent"

        valid_listings.append(listing)

    # Limit to max_results
    comparables = valid_listings[:max_results]

    logger.info(f"Found {len(comparables)} eBay comparables (from {len(listings)} raw)")
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
