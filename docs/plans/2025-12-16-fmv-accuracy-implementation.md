# FMV Accuracy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make FMV lookup context-aware so it finds actual comparables for multi-volume sets and premium bindings.

**Architecture:** Pass full book metadata to FMV lookup, build context-aware search queries via templates, use Claude to filter results by relevance tier (high/medium/low), weight FMV calculation by relevance.

**Tech Stack:** Python 3.12, FastAPI, AWS Bedrock (Claude), pytest

**Worktree:** `/Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy`

**Design Doc:** `docs/plans/2025-12-16-fmv-accuracy-design.md`

---

## Task 1: Add fmv_confidence Field to Schema

**Files:**
- Modify: `backend/app/schemas/eval_runbook.py`
- Test: `backend/tests/test_schemas.py` (if exists, otherwise skip test)

**Step 1: Add fmv_confidence field to EvalRunbookBase**

In `backend/app/schemas/eval_runbook.py`, add after `fmv_notes`:

```python
fmv_confidence: str | None = None  # "high", "medium", "low"
```

**Step 2: Verify schema compiles**

Run: `cd backend && poetry run python -c "from app.schemas.eval_runbook import EvalRunbookBase; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy add backend/app/schemas/eval_runbook.py
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy commit -m "feat: Add fmv_confidence field to eval runbook schema"
```

---

## Task 2: Create Context-Aware Query Builder

**Files:**
- Modify: `backend/app/services/fmv_lookup.py`
- Test: `backend/tests/test_fmv_lookup.py` (create if not exists)

**Step 1: Write failing test for query builder**

Create `backend/tests/test_fmv_lookup.py`:

```python
"""Tests for FMV lookup service."""

import pytest

from app.services.fmv_lookup import _build_context_aware_query


class TestBuildContextAwareQuery:
    """Tests for _build_context_aware_query function."""

    def test_basic_title_and_author(self):
        """Basic query with just title and author."""
        result = _build_context_aware_query(
            title="Vanity Fair",
            author="Thackeray",
        )
        assert "vanity fair" in result.lower()
        assert "thackeray" in result.lower()

    def test_multi_volume_set(self):
        """Query includes volume count for multi-volume sets."""
        result = _build_context_aware_query(
            title="Life of Scott",
            author="Lockhart",
            volumes=7,
        )
        assert "7 volumes" in result.lower() or "7 vol" in result.lower()

    def test_binding_type_morocco(self):
        """Query includes morocco for morocco bindings."""
        result = _build_context_aware_query(
            title="Essays of Elia",
            author="Lamb",
            binding_type="Full morocco",
        )
        assert "morocco" in result.lower()

    def test_binding_type_calf(self):
        """Query includes calf for calf bindings."""
        result = _build_context_aware_query(
            title="Essays of Elia",
            author="Lamb",
            binding_type="Full polished calf",
        )
        assert "calf" in result.lower()

    def test_first_edition(self):
        """Query includes first edition when specified."""
        result = _build_context_aware_query(
            title="Origin of Species",
            author="Darwin",
            edition="First Edition",
        )
        assert "first edition" in result.lower()

    def test_binder_attribution(self):
        """Query includes binder name when specified."""
        result = _build_context_aware_query(
            title="Essays of Elia",
            author="Lamb",
            binder="Riviere",
        )
        assert "riviere" in result.lower()

    def test_full_metadata(self):
        """Query with all metadata fields."""
        result = _build_context_aware_query(
            title="Memoirs of the Life of Sir Walter Scott",
            author="John Gibson Lockhart",
            volumes=7,
            binding_type="Full polished calf",
            binder="J. Leighton",
            edition="First Edition",
        )
        # Should contain key terms
        assert "scott" in result.lower()
        assert "lockhart" in result.lower()
        assert "7 volumes" in result.lower() or "7 vol" in result.lower()
        assert "calf" in result.lower()
        assert "first edition" in result.lower()
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy/backend && poetry run pytest tests/test_fmv_lookup.py -v`
Expected: FAIL with "cannot import name '_build_context_aware_query'"

**Step 3: Implement _build_context_aware_query**

In `backend/app/services/fmv_lookup.py`, add after `_build_search_query`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy/backend && poetry run pytest tests/test_fmv_lookup.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy add backend/app/services/fmv_lookup.py backend/tests/test_fmv_lookup.py
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy commit -m "feat: Add context-aware query builder for FMV lookup"
```

---

## Task 3: Create Claude Filtering Function

**Files:**
- Modify: `backend/app/services/fmv_lookup.py`
- Test: `backend/tests/test_fmv_lookup.py`

**Step 1: Write failing test for Claude filtering**

Add to `backend/tests/test_fmv_lookup.py`:

```python
from unittest.mock import MagicMock, patch


class TestFilterListingsWithClaude:
    """Tests for _filter_listings_with_claude function."""

    @patch("app.services.fmv_lookup.get_bedrock_client")
    @patch("app.services.fmv_lookup.get_model_id")
    def test_filters_by_relevance(self, mock_model_id, mock_client):
        """Claude filters listings and adds relevance scores."""
        from app.services.fmv_lookup import _filter_listings_with_claude

        # Mock Claude response
        mock_response = MagicMock()
        mock_response.__getitem__ = lambda self, key: {
            "body": MagicMock(
                read=lambda: b'{"content": [{"text": "[{\\"title\\": \\"7 vol set\\", \\"price\\": 1000, \\"relevance\\": \\"high\\"}, {\\"title\\": \\"single vol\\", \\"price\\": 50, \\"relevance\\": \\"low\\"}]"}]}'
            )
        }[key]
        mock_client.return_value.invoke_model.return_value = mock_response
        mock_model_id.return_value = "anthropic.claude-3-sonnet"

        listings = [
            {"title": "7 vol set", "price": 1000},
            {"title": "single vol", "price": 50},
        ]
        book_metadata = {
            "title": "Life of Scott",
            "author": "Lockhart",
            "volumes": 7,
        }

        result = _filter_listings_with_claude(listings, book_metadata)

        # Should only return high/medium relevance
        assert len(result) == 1
        assert result[0]["relevance"] == "high"

    @patch("app.services.fmv_lookup.get_bedrock_client")
    @patch("app.services.fmv_lookup.get_model_id")
    def test_handles_empty_listings(self, mock_model_id, mock_client):
        """Returns empty list for empty input."""
        from app.services.fmv_lookup import _filter_listings_with_claude

        result = _filter_listings_with_claude([], {"title": "Test"})
        assert result == []
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy/backend && poetry run pytest tests/test_fmv_lookup.py::TestFilterListingsWithClaude -v`
Expected: FAIL with "cannot import name '_filter_listings_with_claude'"

**Step 3: Implement _filter_listings_with_claude**

In `backend/app/services/fmv_lookup.py`, add:

```python
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
            return [l for l in filtered if l.get("relevance") in ("high", "medium")]

        logger.warning("No JSON array found in Claude filtering response")
        return []

    except Exception as e:
        logger.error(f"Claude filtering failed: {e}")
        # Fall back to returning all listings with medium relevance
        return [{"relevance": "medium", **l} for l in listings]
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy/backend && poetry run pytest tests/test_fmv_lookup.py::TestFilterListingsWithClaude -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy add backend/app/services/fmv_lookup.py backend/tests/test_fmv_lookup.py
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy commit -m "feat: Add Claude filtering for listing relevance"
```

---

## Task 4: Create Weighted FMV Calculation

**Files:**
- Modify: `backend/app/services/fmv_lookup.py`
- Test: `backend/tests/test_fmv_lookup.py`

**Step 1: Write failing test for weighted FMV**

Add to `backend/tests/test_fmv_lookup.py`:

```python
class TestCalculateWeightedFmv:
    """Tests for _calculate_weighted_fmv function."""

    def test_high_relevance_only(self):
        """Uses only high relevance listings when sufficient."""
        from app.services.fmv_lookup import _calculate_weighted_fmv

        listings = [
            {"price": 1000, "relevance": "high"},
            {"price": 1200, "relevance": "high"},
            {"price": 1400, "relevance": "high"},
            {"price": 100, "relevance": "medium"},
            {"price": 50, "relevance": "low"},
        ]

        result = _calculate_weighted_fmv(listings)

        # Should use only high relevance (1000, 1200, 1400)
        assert result["fmv_low"] == 1000
        assert result["fmv_high"] == 1400
        assert result["fmv_confidence"] == "high"

    def test_falls_back_to_medium(self):
        """Falls back to medium when insufficient high."""
        from app.services.fmv_lookup import _calculate_weighted_fmv

        listings = [
            {"price": 1000, "relevance": "high"},
            {"price": 300, "relevance": "medium"},
            {"price": 400, "relevance": "medium"},
            {"price": 500, "relevance": "medium"},
        ]

        result = _calculate_weighted_fmv(listings)

        # Should include medium (only 1 high)
        assert result["fmv_confidence"] == "medium"

    def test_insufficient_data(self):
        """Returns low confidence when insufficient data."""
        from app.services.fmv_lookup import _calculate_weighted_fmv

        listings = [
            {"price": 1000, "relevance": "high"},
        ]

        result = _calculate_weighted_fmv(listings)

        assert result["fmv_confidence"] == "low"
        assert "Insufficient" in result["fmv_notes"]

    def test_empty_listings(self):
        """Handles empty listings gracefully."""
        from app.services.fmv_lookup import _calculate_weighted_fmv

        result = _calculate_weighted_fmv([])

        assert result["fmv_low"] is None
        assert result["fmv_high"] is None
        assert result["fmv_confidence"] == "low"
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy/backend && poetry run pytest tests/test_fmv_lookup.py::TestCalculateWeightedFmv -v`
Expected: FAIL with "cannot import name '_calculate_weighted_fmv'"

**Step 3: Implement _calculate_weighted_fmv**

In `backend/app/services/fmv_lookup.py`, add:

```python
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
    high = [l for l in listings if l.get("relevance") == "high" and l.get("price")]
    medium = [l for l in listings if l.get("relevance") == "medium" and l.get("price")]

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
    prices = sorted([float(l["price"]) for l in use_listings])
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
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy/backend && poetry run pytest tests/test_fmv_lookup.py::TestCalculateWeightedFmv -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy add backend/app/services/fmv_lookup.py backend/tests/test_fmv_lookup.py
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy commit -m "feat: Add weighted FMV calculation by relevance tier"
```

---

## Task 5: Update lookup_ebay_comparables Signature

**Files:**
- Modify: `backend/app/services/fmv_lookup.py`

**Step 1: Update function signature and implementation**

In `backend/app/services/fmv_lookup.py`, replace the existing `lookup_ebay_comparables` function:

```python
def lookup_ebay_comparables(
    title: str,
    author: str | None = None,
    volumes: int = 1,
    binding_type: str | None = None,
    binder: str | None = None,
    edition: str | None = None,
    max_results: int = 5,
) -> list[dict]:
    """Look up comparable sold listings on eBay.

    Uses scraper Lambda with Playwright browser to avoid eBay bot detection.
    The scraper extracts listings directly via JavaScript, then Claude filters
    by relevance to the target book metadata.

    Args:
        title: Book title
        author: Optional author name
        volumes: Number of volumes (for matching multi-volume sets)
        binding_type: Binding type (morocco, calf, etc.)
        binder: Binder name (Riviere, Zaehnsdorf, etc.)
        edition: Edition info (First Edition, etc.)
        max_results: Maximum comparables to return

    Returns:
        List of comparable dicts with title, price, url, condition, sold_date, relevance
    """
    # Build context-aware query
    query = _build_context_aware_query(title, author, volumes, binding_type, binder, edition)
    url = EBAY_SOLD_SEARCH_URL.format(query=query)

    logger.info(f"Searching eBay sold listings with context-aware query: {url}")

    # Fetch raw listings via scraper
    listings = _fetch_listings_via_scraper_lambda(url)

    if listings is None:
        logger.warning("Failed to fetch eBay search results via scraper")
        return []

    if not listings:
        # Try fallback with simpler query
        logger.info("No results with context-aware query, trying fallback")
        fallback_query = _build_search_query(title, author)
        fallback_url = EBAY_SOLD_SEARCH_URL.format(query=fallback_query)
        listings = _fetch_listings_via_scraper_lambda(fallback_url)

        if not listings:
            logger.info("No eBay listings found even with fallback query")
            return []

    logger.info(f"Scraper returned {len(listings)} raw eBay listings")

    # Filter by relevance using Claude
    book_metadata = {
        "title": title,
        "author": author,
        "volumes": volumes,
        "binding_type": binding_type,
        "binder": binder,
        "edition": edition,
    }
    filtered = _filter_listings_with_claude(listings, book_metadata)

    logger.info(f"Claude filtered to {len(filtered)} relevant listings")

    # Ensure sold_date has a value
    for listing in filtered:
        if not listing.get("sold_date"):
            listing["sold_date"] = "recent"

    comparables = filtered[:max_results]
    logger.info(f"Returning {len(comparables)} eBay comparables")
    return comparables
```

**Step 2: Verify existing tests still pass**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy/backend && poetry run pytest tests/test_fmv_lookup.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy add backend/app/services/fmv_lookup.py
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy commit -m "feat: Update lookup_ebay_comparables with full metadata support"
```

---

## Task 6: Update lookup_fmv to Use Weighted Calculation

**Files:**
- Modify: `backend/app/services/fmv_lookup.py`

**Step 1: Update lookup_fmv function**

In `backend/app/services/fmv_lookup.py`, replace the existing `lookup_fmv` function:

```python
def lookup_fmv(
    title: str,
    author: str | None = None,
    volumes: int = 1,
    binding_type: str | None = None,
    binder: str | None = None,
    edition: str | None = None,
    max_per_source: int = 5,
) -> dict:
    """Look up Fair Market Value from multiple sources.

    Args:
        title: Book title
        author: Optional author name
        volumes: Number of volumes
        binding_type: Binding type
        binder: Binder name
        edition: Edition info
        max_per_source: Maximum comparables per source

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
        title, author, volumes, binding_type, binder, edition, max_per_source
    )
    abebooks = lookup_abebooks_comparables(title, author, max_per_source)

    # Use weighted FMV calculation
    all_listings = ebay + abebooks
    fmv_result = _calculate_weighted_fmv(all_listings)

    return {
        "ebay_comparables": ebay,
        "abebooks_comparables": abebooks,
        "fmv_low": fmv_result["fmv_low"],
        "fmv_high": fmv_result["fmv_high"],
        "fmv_confidence": fmv_result["fmv_confidence"],
        "fmv_notes": fmv_result["fmv_notes"],
    }
```

**Step 2: Commit**

```bash
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy add backend/app/services/fmv_lookup.py
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy commit -m "feat: Update lookup_fmv to use weighted calculation"
```

---

## Task 7: Update Eval Runbook Endpoint to Pass Metadata

**Files:**
- Modify: `backend/app/api/v1/endpoints/eval_runbook.py`

**Step 1: Find and update the FMV lookup call**

First, read the current endpoint to find where lookup_fmv is called:

```bash
grep -n "lookup_fmv\|lookup_ebay" /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy/backend/app/api/v1/endpoints/eval_runbook.py
```

**Step 2: Update the call to pass full metadata**

Where `lookup_fmv` or `lookup_ebay_comparables` is called, update to pass book metadata:

```python
# Before (example)
fmv_data = lookup_fmv(book.title, book.author.name if book.author else None)

# After
fmv_data = lookup_fmv(
    title=book.title,
    author=book.author.name if book.author else None,
    volumes=book.volumes or 1,
    binding_type=book.binding_type,
    binder=book.binder.name if book.binder else None,
    edition=book.edition,
)
```

**Step 3: Verify linting passes**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy/backend && poetry run ruff check app/api/v1/endpoints/eval_runbook.py`
Expected: No errors

**Step 4: Commit**

```bash
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy add backend/app/api/v1/endpoints/eval_runbook.py
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy commit -m "feat: Pass full book metadata to FMV lookup in eval runbook"
```

---

## Task 8: Run Full Test Suite and Lint

**Step 1: Run linting**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy/backend && poetry run ruff check .`
Expected: No errors (or fix any that appear)

**Step 2: Run formatting check**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy/backend && poetry run ruff format --check .`
Expected: No formatting issues (or run `ruff format .` to fix)

**Step 3: Run full test suite**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy/backend && poetry run pytest tests/ -q`
Expected: All tests pass (except known bedrock client test)

**Step 4: Commit any fixes**

```bash
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy add -A
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy commit -m "fix: Address linting and test issues"
```

---

## Task 9: Create PR to Staging

**Step 1: Push branch**

```bash
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-fmv-accuracy push -u origin fix/fmv-accuracy
```

**Step 2: Create PR**

```bash
gh pr create --repo markthebest12/bluemoxon --base staging --head fix/fmv-accuracy --title "fix: Context-aware FMV lookup for accurate comparables (#384)" --body "## Summary
- Add context-aware query builder that includes volume count, binding type, edition
- Add Claude filtering to rate listing relevance (high/medium/low)
- Add weighted FMV calculation that prioritizes high-relevance comparables
- Pass full book metadata from eval runbook to FMV lookup
- Add fmv_confidence field to response

## Test Plan
- [ ] Unit tests pass for new functions
- [ ] Manual test with multi-volume set (e.g., 7-vol Lockhart)
- [ ] Verify FMV range reflects comparable sets, not single volumes

Fixes #384"
```

**Step 3: Wait for CI**

```bash
gh pr checks --repo markthebest12/bluemoxon <PR_NUMBER> --watch
```

---

## Verification Checklist

After merging to staging:

- [ ] Trigger eval runbook refresh for a multi-volume set
- [ ] Verify eBay comparables are relevant (matching volume count)
- [ ] Verify FMV range reflects set prices, not single volume prices
- [ ] Verify fmv_confidence field is populated
