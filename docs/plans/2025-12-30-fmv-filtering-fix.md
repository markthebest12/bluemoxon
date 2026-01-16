# FMV Filtering Fix - Issue #709 Phase 2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix Claude's relevance filtering so it actually returns comparable listings instead of filtering all of them out

**Architecture:** Modify `_filter_listings_with_claude()` in `fmv_lookup.py` to:

1. Remove strict era-based rejection that rejects valid comparables
2. Add fallback when all listings rated "low" - return top matches by binding/condition
3. Focus filtering on binding type and condition (per book-collection methodology)

**Tech Stack:** Python, AWS Bedrock (Claude), pytest

**Context:** The scraper correctly extracts 60 eBay listings, but Claude's relevance filter rejects all of them as "low" relevance due to overly strict era matching ("within ~50 years"). The book-collection project's methodology focuses on binding type (half leather vs full morocco) and condition matching instead of era.

---

## Task 1: Write Failing Test for Low Relevance Fallback

**Files:**

- Modify: `backend/tests/test_fmv_lookup.py`

**Step 1: Write the failing test**

Add this test to the `TestFilterListingsWithClaude` class:

```python
@patch("app.services.fmv_lookup.get_bedrock_client")
@patch("app.services.fmv_lookup.get_model_id")
def test_fallback_when_all_low_relevance(self, mock_model_id, mock_client):
    """When Claude rates all listings as 'low', return top 5 as fallback."""
    from app.services.fmv_lookup import _filter_listings_with_claude

    # Mock Claude response - all listings rated "low"
    low_listings = [
        {"title": "Book 1", "price": 500, "relevance": "low"},
        {"title": "Book 2", "price": 450, "relevance": "low"},
        {"title": "Book 3", "price": 400, "relevance": "low"},
        {"title": "Book 4", "price": 350, "relevance": "low"},
        {"title": "Book 5", "price": 300, "relevance": "low"},
        {"title": "Book 6", "price": 250, "relevance": "low"},
    ]
    mock_response = MagicMock()
    mock_response.__getitem__ = lambda self, key: {
        "body": MagicMock(
            read=lambda: json.dumps({
                "content": [{"text": json.dumps(low_listings)}]
            }).encode()
        )
    }[key]
    mock_client.return_value.invoke_model.return_value = mock_response
    mock_model_id.return_value = "anthropic.claude-3-sonnet"

    listings = [
        {"title": "Book 1", "price": 500},
        {"title": "Book 2", "price": 450},
        {"title": "Book 3", "price": 400},
        {"title": "Book 4", "price": 350},
        {"title": "Book 5", "price": 300},
        {"title": "Book 6", "price": 250},
    ]
    book_metadata = {
        "title": "Origin of Species",
        "author": "Darwin",
        "publication_year": 1859,
    }

    result = _filter_listings_with_claude(listings, book_metadata)

    # Should return top 5 low-relevance listings as fallback
    assert len(result) == 5
    # All should be marked as "low" relevance with fallback indicator
    for item in result:
        assert item["relevance"] in ("low", "fallback")
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/mark/projects/bluemoxon/backend && poetry run pytest tests/test_fmv_lookup.py::TestFilterListingsWithClaude::test_fallback_when_all_low_relevance -v`

Expected: FAIL - currently returns empty list when all are "low"

**Step 3: This task is test-only - implementation in Task 2**

---

## Task 2: Implement Low Relevance Fallback

**Files:**

- Modify: `backend/app/services/fmv_lookup.py:259-352` (`_filter_listings_with_claude` function)

**Step 1: Modify the function to add fallback logic**

Find the `_filter_listings_with_claude` function (lines 259-352) and replace the filtering logic at the end:

Current code (approximately lines 339-352):

```python
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
```

Replace with:

```python
        # Extract JSON from response
        json_match = re.search(r"\[[\s\S]*\]", result_text)
        if json_match:
            all_rated = json.loads(json_match.group())

            # First try high/medium relevance
            high_medium = [item for item in all_rated if item.get("relevance") in ("high", "medium")]

            if high_medium:
                logger.info(f"Returning {len(high_medium)} high/medium relevance listings")
                return high_medium

            # Fallback: if all are "low", return top 5 by price proximity
            # This prevents returning empty comparables when Claude is too strict
            low_items = [item for item in all_rated if item.get("relevance") == "low"]
            if low_items:
                logger.warning(
                    f"All {len(low_items)} listings rated 'low' relevance. "
                    "Returning top 5 as fallback."
                )
                # Mark as fallback and return top 5
                fallback = low_items[:5]
                for item in fallback:
                    item["relevance"] = "fallback"
                return fallback

            logger.warning("No listings with relevance ratings found")
            return []

        logger.warning("No JSON array found in Claude filtering response")
        return []

    except Exception as e:
        logger.error(f"Claude filtering failed: {e}")
        # Fall back to returning all listings with medium relevance
        return [{"relevance": "medium", **item} for item in listings]
```

**Step 2: Run the test to verify it passes**

Run: `cd /Users/mark/projects/bluemoxon/backend && poetry run pytest tests/test_fmv_lookup.py::TestFilterListingsWithClaude::test_fallback_when_all_low_relevance -v`

Expected: PASS

**Step 3: Run all FMV tests to ensure no regressions**

Run: `cd /Users/mark/projects/bluemoxon/backend && poetry run pytest tests/test_fmv_lookup.py -v`

Expected: All tests PASS

**Step 4: Commit**

```bash
git add backend/tests/test_fmv_lookup.py backend/app/services/fmv_lookup.py
git commit -m "feat(fmv): add fallback when all listings rated low relevance (#709)"
```

---

## Task 3: Write Failing Test for Relaxed Era Filtering

**Files:**

- Modify: `backend/tests/test_fmv_lookup.py`

**Step 1: Write the failing test**

Add this test to the `TestFilterListingsWithClaude` class:

```python
@patch("app.services.fmv_lookup.get_bedrock_client")
@patch("app.services.fmv_lookup.get_model_id")
def test_prompt_focuses_on_binding_not_era(self, mock_model_id, mock_client):
    """Claude prompt should focus on binding type match, not strict era matching."""
    from app.services.fmv_lookup import _filter_listings_with_claude

    mock_response = MagicMock()
    mock_response.__getitem__ = lambda self, key: {
        "body": MagicMock(
            read=lambda: json.dumps({
                "content": [{"text": "[]"}]
            }).encode()
        )
    }[key]
    mock_client.return_value.invoke_model.return_value = mock_response
    mock_model_id.return_value = "anthropic.claude-3-sonnet"

    listings = [{"title": "Test", "price": 100}]
    book_metadata = {
        "title": "Origin of Species",
        "author": "Darwin",
        "publication_year": 1859,
        "binding_type": "Full morocco",
    }

    _filter_listings_with_claude(listings, book_metadata)

    # Check the prompt sent to Claude
    call_args = mock_client.return_value.invoke_model.call_args
    body = json.loads(call_args.kwargs["body"])
    prompt = body["messages"][0]["content"]

    # Prompt should NOT contain strict era rejection language
    assert "within ~50 years" not in prompt.lower()
    assert "post-1950 are low" not in prompt.lower()

    # Prompt SHOULD mention binding type matching
    assert "binding" in prompt.lower()
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/mark/projects/bluemoxon/backend && poetry run pytest tests/test_fmv_lookup.py::TestFilterListingsWithClaude::test_prompt_focuses_on_binding_not_era -v`

Expected: FAIL - current prompt contains "within ~50 years"

**Step 3: This task is test-only - implementation in Task 4**

---

## Task 4: Relax Era Filtering in Claude Prompt

**Files:**

- Modify: `backend/app/services/fmv_lookup.py:259-352` (`_filter_listings_with_claude` function)

**Step 1: Modify the prompt to focus on binding/condition**

Find the era_guidance section in the prompt (around lines 293-301):

Current code:

```python
    # Build era guidance if we have a publication year
    pub_year = book_metadata.get("publication_year")
    era_guidance = ""
    if pub_year:
        era_guidance = f"""
CRITICAL: The target book was published in {pub_year}. Modern reprints, facsimiles, or later editions
from different eras are NOT comparable. A listing must be from a similar era (within ~50 years)
to be rated HIGH. Modern reprints (post-1950) of antique books should be rated LOW."""
```

Replace with:

```python
    # Build filtering guidance focusing on binding and condition
    pub_year = book_metadata.get("publication_year")
    binding_type = book_metadata.get("binding_type", "")

    # Build filtering guidance
    filter_guidance_parts = []

    if pub_year:
        filter_guidance_parts.append(
            f"The target book was published in {pub_year}. "
            "Modern reprints and facsimiles should be noted but are still useful for price reference."
        )

    if binding_type:
        # Per book-collection methodology: half leather is 50-60% of full morocco value
        filter_guidance_parts.append(
            f"BINDING TYPE is critical: target has {binding_type}. "
            "Half leather vs full morocco is a 50-60% value difference. "
            "Match binding type closely when rating relevance."
        )

    filter_guidance = "\n".join(filter_guidance_parts) if filter_guidance_parts else ""
```

**Step 2: Update the prompt template to use the new guidance**

Find the prompt template (around line 302-315) and update the era_guidance reference:

Current:

```python
{era_guidance}
```

Replace with:

```python
{filter_guidance}
```

Also update the variable name in the f-string from `era_guidance` to `filter_guidance`.

**Step 3: Run the test to verify it passes**

Run: `cd /Users/mark/projects/bluemoxon/backend && poetry run pytest tests/test_fmv_lookup.py::TestFilterListingsWithClaude::test_prompt_focuses_on_binding_not_era -v`

Expected: PASS

**Step 4: Run all FMV tests**

Run: `cd /Users/mark/projects/bluemoxon/backend && poetry run pytest tests/test_fmv_lookup.py -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/app/services/fmv_lookup.py backend/tests/test_fmv_lookup.py
git commit -m "feat(fmv): relax era filtering, focus on binding type (#709)"
```

---

## Task 5: Update FMV Calculation to Handle Fallback Relevance

**Files:**

- Modify: `backend/app/services/fmv_lookup.py` (`_calculate_weighted_fmv` function)
- Modify: `backend/tests/test_fmv_lookup.py`

**Step 1: Write failing test for fallback relevance handling**

Add this test to the `TestCalculateWeightedFmv` class:

```python
def test_handles_fallback_relevance(self):
    """Treats 'fallback' relevance as low confidence but usable."""
    from app.services.fmv_lookup import _calculate_weighted_fmv

    listings = [
        {"price": 500, "relevance": "fallback"},
        {"price": 400, "relevance": "fallback"},
        {"price": 300, "relevance": "fallback"},
    ]

    result = _calculate_weighted_fmv(listings)

    # Should use fallback listings with low confidence
    assert result["fmv_low"] == 300
    assert result["fmv_high"] == 500
    assert result["fmv_confidence"] == "low"
    assert "fallback" in result["fmv_notes"].lower() or "insufficient" in result["fmv_notes"].lower()
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/mark/projects/bluemoxon/backend && poetry run pytest tests/test_fmv_lookup.py::TestCalculateWeightedFmv::test_handles_fallback_relevance -v`

Expected: FAIL - current code doesn't recognize "fallback" relevance

**Step 3: Implement fallback handling in _calculate_weighted_fmv**

Find the function (around line 355) and update the relevance filtering:

Current code (approximately lines 373-395):

```python
    # Separate by relevance
    high = [item for item in listings if item.get("relevance") == "high" and item.get("price")]
    medium = [item for item in listings if item.get("relevance") == "medium" and item.get("price")]
```

Add after medium line:

```python
    fallback = [item for item in listings if item.get("relevance") == "fallback" and item.get("price")]
```

Then update the decision logic (around lines 377-395):

Current:

```python
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
```

Replace with:

```python
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
    elif fallback:
        # Use fallback listings when no high/medium available
        use_listings = fallback
        confidence = "low"
        notes = f"Based on {len(fallback)} fallback comparables (all others rated low relevance)"
    else:
        return {
            "fmv_low": None,
            "fmv_high": None,
            "fmv_confidence": "low",
            "fmv_notes": "No relevant comparables found",
        }
```

**Step 4: Run the test to verify it passes**

Run: `cd /Users/mark/projects/bluemoxon/backend && poetry run pytest tests/test_fmv_lookup.py::TestCalculateWeightedFmv::test_handles_fallback_relevance -v`

Expected: PASS

**Step 5: Run all FMV tests**

Run: `cd /Users/mark/projects/bluemoxon/backend && poetry run pytest tests/test_fmv_lookup.py -v`

Expected: All tests PASS

**Step 6: Commit**

```bash
git add backend/app/services/fmv_lookup.py backend/tests/test_fmv_lookup.py
git commit -m "feat(fmv): handle fallback relevance in FMV calculation (#709)"
```

---

## Task 6: Run Full Linting and Tests

**Files:**

- None (verification only)

**Step 1: Run linter**

Run: `cd /Users/mark/projects/bluemoxon/backend && poetry run ruff check app/services/fmv_lookup.py tests/test_fmv_lookup.py`

Expected: No errors

**Step 2: Run formatter check**

Run: `cd /Users/mark/projects/bluemoxon/backend && poetry run ruff format --check app/services/fmv_lookup.py tests/test_fmv_lookup.py`

Expected: Would not reformat (or run `ruff format` if needed)

**Step 3: Run all backend tests**

Run: `cd /Users/mark/projects/bluemoxon/backend && poetry run pytest tests/ -v`

Expected: All tests PASS

**Step 4: If any formatting needed, commit**

```bash
git add -A
git commit -m "style: format fmv_lookup code"
```

---

## Task 7: Create Branch and Push to Staging

**Files:**

- None (git operations only)

**Step 1: Check current branch**

Run: `git branch`

**Step 2: Create feature branch from staging (if not already)**

Run: `git checkout -b fix/fmv-filtering-709-phase2 origin/staging`

Note: If commits were made on a different branch, cherry-pick or squash them to this branch.

**Step 3: Push branch**

Run: `git push -u origin fix/fmv-filtering-709-phase2`

**Step 4: Create PR**

Run: `gh pr create --base staging --title "fix(fmv): relax Claude filtering to return comparables (#709)" --body "## Summary

- Add fallback when all listings rated 'low' relevance - returns top 5 instead of empty
- Relax era-based filtering - focus on binding type match per book-collection methodology
- Handle 'fallback' relevance in FMV calculation

## Root Cause

Claude's relevance filtering was too strict:

1. 'within ~50 years' era requirement rejected valid comparables
2. No fallback when all items rated 'low' - returned empty array
3. Binding type matching wasn't emphasized

## Test Plan

- [x] Unit tests for fallback behavior
- [x] Unit tests for relaxed prompt
- [x] All FMV tests pass
- [ ] CI passes
- [ ] Test in staging: \`bmx-api GET /books/537/eval-runbook\` returns comparables

Closes #709 (Phase 2)"`

**Step 5: Wait for CI**

Run: `gh pr checks --watch`

Expected: All checks pass

---

## Task 8: Validate in Staging

**Files:**

- None (API testing only)

**Step 1: Wait for staging deploy**

After PR is merged to staging, wait for deploy workflow.

**Step 2: Test the fix**

Run: `bmx-api GET "/books/537/eval-runbook" | jq '{ebay_count: (.ebay_comparables | length), abebooks_count: (.abebooks_comparables | length), fmv_notes}'`

Expected: `ebay_count > 0` or `abebooks_count > 0`

**Step 3: If validation passes, create promotion PR**

Run: `gh pr create --base main --head staging --title "chore: promote staging to production (fix/fmv-filtering-709-phase2)"`

**STOP: Wait for user review before merging to production**

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Write failing test for low relevance fallback | `tests/test_fmv_lookup.py` |
| 2 | Implement fallback when all "low" | `app/services/fmv_lookup.py` |
| 3 | Write failing test for relaxed era filtering | `tests/test_fmv_lookup.py` |
| 4 | Relax era filtering in prompt | `app/services/fmv_lookup.py` |
| 5 | Handle fallback in FMV calculation | `app/services/fmv_lookup.py`, `tests/test_fmv_lookup.py` |
| 6 | Lint and test all code | verification |
| 7 | Create branch, PR to staging | git |
| 8 | Validate in staging, promote to prod | API testing |
