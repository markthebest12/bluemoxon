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


def _calculate_weighted_fmv(listings: list[dict]) -> dict:
    """Calculate FMV range weighted by relevance tier.

    Args:
        listings: Listings with relevance scores

    Returns:
        Dict with fmv_low, fmv_high, fmv_confidence, fmv_notes
    """
    if not listings:
        return {
            "fmv_low": None,
            "fmv_high": None,
            "fmv_confidence": "low",
            "fmv_notes": "No comparable listings found",
        }

    # Separate by relevance
    high = [item for item in listings if item.get("relevance") == "high" and item.get("price")]
    medium = [item for item in listings if item.get("relevance") == "medium" and item.get("price")]

    # Determine which set to use
    if len(high) >= 2:
        use_listings = high
        confidence = "high"
        notes = f"Based on {len(high)} highly relevant comparables"
    elif len(high) + len(medium) >= 3:
        use_listings = high + medium
        confidence = "medium"
        notes = f"Based on {len(high)} high + {len(medium)} medium relevance comparables"
    elif high or medium:
        use_listings = high + medium
        confidence = "low"
        notes = f"Insufficient comparable data ({len(high)} high, {len(medium)} medium)"
    else:
        return {
            "fmv_low": None,
            "fmv_high": None,
            "fmv_confidence": "low",
            "fmv_notes": "No relevant comparables found",
        }

    # Extract and sort prices
    prices = sorted([float(item["price"]) for item in use_listings])
    n = len(prices)

    # Calculate range (25th/75th percentile or min/max for small sets)
    if n >= 4:
        fmv_low = prices[n // 4]
        fmv_high = prices[3 * n // 4]
    else:
        fmv_low = prices[0]
        fmv_high = prices[-1]

    return {
        "fmv_low": fmv_low,
        "fmv_high": fmv_high,
        "fmv_confidence": confidence,
        "fmv_notes": notes,
    }


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

    # Source-specific prompt text
    if source == "ebay":
        listing_type = "sold book listings"
        listing_context = "Items shown have been sold."
        price_label = "Sale price"
        date_field = "sold_date"
        date_desc = "When it sold"
    else:  # abebooks
        listing_type = "book listings currently for sale"
        listing_context = "Items shown are available for purchase."
        price_label = "Asking price"
        date_field = "list_date"
        date_desc = "When listed"

    prompt = f"""Extract the top {max_results} most relevant {listing_type} from this {source} search results page.

{listing_context}

The book being evaluated is: "{book_title}"

Only include listings that appear to be the SAME book or very similar editions.
Skip listings that are clearly different books.

For each relevant listing, extract:
- title: The listing title
- price: {price_label} in USD (number only, no currency symbol)
- url: Full URL to the listing (if available)
- condition: Condition description if stated
- {date_field}: {date_desc} (if available, format: YYYY-MM-DD or "recent" if not specific)
- relevance: "high", "medium", or "low" based on how closely it matches the target book

Return JSON array only, no other text:
[
  {{"title": "...", "price": 150.00, "url": "...", "condition": "...", "{date_field}": "...", "relevance": "high"}},
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
    volumes: int = 1,
    binding_type: str | None = None,
    binder: str | None = None,
    edition: str | None = None,
) -> list[dict]:
    """Look up comparable sold listings on eBay.

    Uses scraper Lambda with Playwright browser to avoid eBay bot detection.
    The scraper extracts listings directly via JavaScript, avoiding the
    truncation issue where raw HTML was too large for processing.

    Args:
        title: Book title
        author: Optional author name
        max_results: Maximum comparables to return
        volumes: Number of volumes (for context-aware query)
        binding_type: Binding type (for context-aware query)
        binder: Binder name (for context-aware query)
        edition: Edition info (for context-aware query)

    Returns:
        List of comparable dicts with title, price, url, condition, sold_date, relevance
    """
    # Use context-aware query if we have metadata beyond title/author
    if volumes > 1 or binding_type or binder or edition:
        query = _build_context_aware_query(
            title=title,
            author=author,
            volumes=volumes,
            binding_type=binding_type,
            binder=binder,
            edition=edition,
        )
    else:
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

    # Filter listings with valid prices
    valid_listings = []
    for listing in listings:
        if not listing.get("price"):
            continue
        if not listing.get("sold_date"):
            listing["sold_date"] = "recent"
        valid_listings.append(listing)

    if not valid_listings:
        logger.info("No valid eBay listings (all missing prices)")
        return []

    # Use Claude to filter by relevance
    book_metadata = {
        "title": title,
        "author": author,
        "volumes": volumes,
        "binding_type": binding_type,
        "binder": binder,
        "edition": edition,
    }
    filtered_listings = _filter_listings_with_claude(valid_listings, book_metadata)

    # Limit to max_results
    comparables = filtered_listings[:max_results]

    logger.info(f"Found {len(comparables)} eBay comparables (from {len(listings)} raw)")
    return comparables


def lookup_abebooks_comparables(
    title: str,
    author: str | None = None,
    max_results: int = 5,
    volumes: int = 1,
    binding_type: str | None = None,
    binder: str | None = None,
    edition: str | None = None,
) -> list[dict]:
    """Look up comparable listings on AbeBooks.

    Args:
        title: Book title
        author: Optional author name
        max_results: Maximum comparables to return
        volumes: Number of volumes (for context-aware query)
        binding_type: Binding type (for context-aware query)
        binder: Binder name (for context-aware query)
        edition: Edition info (for context-aware query)

    Returns:
        List of comparable dicts with title, price, url, condition
    """
    # Use context-aware query if we have metadata beyond title/author
    if volumes > 1 or binding_type or binder or edition:
        query = _build_context_aware_query(
            title=title,
            author=author,
            volumes=volumes,
            binding_type=binding_type,
            binder=binder,
            edition=edition,
        )
    else:
        query = _build_search_query(title, author)
    url = ABEBOOKS_SEARCH_URL.format(query=query)

    logger.info(f"Searching AbeBooks: {url}")
    html = _fetch_search_page(url)

    if not html:
        logger.warning("Failed to fetch AbeBooks search results")
        return []

    comparables = _extract_comparables_with_claude(html, "abebooks", title, max_results)

    # Filter out comparables without prices (same as eBay path)
    valid_comparables = [c for c in comparables if c.get("price")]
    if len(valid_comparables) < len(comparables):
        logger.info(
            f"Filtered out {len(comparables) - len(valid_comparables)} AbeBooks comparables without prices"
        )

    logger.info(f"Found {len(valid_comparables)} AbeBooks comparables")
    return valid_comparables


def lookup_fmv(
    title: str,
    author: str | None = None,
    max_per_source: int = 5,
    volumes: int = 1,
    binding_type: str | None = None,
    binder: str | None = None,
    edition: str | None = None,
) -> dict:
    """Look up Fair Market Value from multiple sources.

    Args:
        title: Book title
        author: Optional author name
        max_per_source: Maximum comparables per source
        volumes: Number of volumes (for context-aware query)
        binding_type: Binding type (for context-aware query)
        binder: Binder name (for context-aware query)
        edition: Edition info (for context-aware query)

    Returns:
        Dict with:
            - ebay_comparables: List of eBay sold listings
            - abebooks_comparables: List of AbeBooks listings
            - fmv_low: Low estimate based on comparables
            - fmv_high: High estimate based on comparables
            - fmv_confidence: Confidence level (high/medium/low)
            - fmv_notes: Summary of FMV analysis
    """
    ebay = lookup_ebay_comparables(
        title=title,
        author=author,
        max_results=max_per_source,
        volumes=volumes,
        binding_type=binding_type,
        binder=binder,
        edition=edition,
    )
    # AbeBooks now uses context-aware query like eBay
    abebooks = lookup_abebooks_comparables(
        title=title,
        author=author,
        max_results=max_per_source,
        volumes=volumes,
        binding_type=binding_type,
        binder=binder,
        edition=edition,
    )

    # Calculate weighted FMV from relevance-scored comparables
    all_listings = ebay + abebooks
    fmv_result = _calculate_weighted_fmv(all_listings)

    # Update notes to include source counts
    if ebay or abebooks:
        fmv_result["fmv_notes"] = (
            f"{fmv_result['fmv_notes']} ({len(ebay)} eBay, {len(abebooks)} AbeBooks)"
        )

    return {
        "ebay_comparables": ebay,
        "abebooks_comparables": abebooks,
        "fmv_low": fmv_result["fmv_low"],
        "fmv_high": fmv_result["fmv_high"],
        "fmv_confidence": fmv_result["fmv_confidence"],
        "fmv_notes": fmv_result["fmv_notes"],
    }
