# AbeBooks FMV Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring AbeBooks FMV lookup to parity with eBay's implementation (context-aware queries + correct prompt for active listings).

**Architecture:** Modify `_extract_comparables_with_claude()` to use source-specific prompt text, and update `lookup_abebooks_comparables()` to accept and use context-aware query parameters.

**Tech Stack:** Python, pytest, httpx, Claude/Bedrock

**Related:** Issue #379, Design doc `docs/plans/2025-12-17-abebooks-fmv-parity-design.md`

---

### Task 1: Add Test for Source-Specific Prompt Text

**Files:**

- Modify: `backend/tests/test_fmv_lookup.py`

**Step 1: Write the failing test**

Add to `test_fmv_lookup.py`:

```python
class TestExtractComparablesPrompt:
    """Tests for _extract_comparables_with_claude prompt variations."""

    @patch("app.services.fmv_lookup.get_bedrock_client")
    @patch("app.services.fmv_lookup.get_model_id")
    def test_ebay_prompt_says_sold_listings(self, mock_model_id, mock_client):
        """eBay extraction prompt asks for sold listings."""
        from app.services.fmv_lookup import _extract_comparables_with_claude

        mock_response = MagicMock()
        mock_response.__getitem__ = lambda self, key: {
            "body": MagicMock(read=lambda: b'{"content": [{"text": "[]"}]}')
        }[key]
        mock_client.return_value.invoke_model.return_value = mock_response
        mock_model_id.return_value = "anthropic.claude-3-sonnet"

        _extract_comparables_with_claude("<html></html>", "ebay", "Test Book")

        # Check the prompt sent to Claude
        call_args = mock_client.return_value.invoke_model.call_args
        body = json.loads(call_args.kwargs["body"])
        prompt = body["messages"][0]["content"]
        assert "sold book listings" in prompt.lower()

    @patch("app.services.fmv_lookup.get_bedrock_client")
    @patch("app.services.fmv_lookup.get_model_id")
    def test_abebooks_prompt_says_active_listings(self, mock_model_id, mock_client):
        """AbeBooks extraction prompt asks for active/for-sale listings."""
        from app.services.fmv_lookup import _extract_comparables_with_claude

        mock_response = MagicMock()
        mock_response.__getitem__ = lambda self, key: {
            "body": MagicMock(read=lambda: b'{"content": [{"text": "[]"}]}')
        }[key]
        mock_client.return_value.invoke_model.return_value = mock_response
        mock_model_id.return_value = "anthropic.claude-3-sonnet"

        _extract_comparables_with_claude("<html></html>", "abebooks", "Test Book")

        # Check the prompt sent to Claude
        call_args = mock_client.return_value.invoke_model.call_args
        body = json.loads(call_args.kwargs["body"])
        prompt = body["messages"][0]["content"]
        assert "for sale" in prompt.lower() or "currently available" in prompt.lower()
        assert "sold" not in prompt.lower()
```

**Step 2: Run test to verify it fails**

Run: `poetry run --directory backend pytest backend/tests/test_fmv_lookup.py::TestExtractComparablesPrompt -v`

Expected: FAIL - both tests will fail because current implementation uses same prompt for both sources.

**Step 3: Commit test (red)**

```bash
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-abebooks-fmv add backend/tests/test_fmv_lookup.py
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-abebooks-fmv commit -m "test: Add tests for source-specific prompt text (red)"
```

---

### Task 2: Implement Source-Specific Prompt Text

**Files:**

- Modify: `backend/app/services/fmv_lookup.py:455-501`

**Step 1: Update `_extract_comparables_with_claude()` function**

Change the prompt construction (around line 476) from:

```python
    prompt = f"""Extract the top {max_results} most relevant sold book listings from this {source} search results page.
```

To:

```python
    # Source-specific listing type
    if source == "ebay":
        listing_type = "sold book listings"
        listing_context = "Items shown have been sold."
    else:  # abebooks
        listing_type = "book listings currently for sale"
        listing_context = "Items shown are available for purchase."

    prompt = f"""Extract the top {max_results} most relevant {listing_type} from this {source} search results page.

{listing_context}
```

**Step 2: Run tests to verify they pass**

Run: `poetry run --directory backend pytest backend/tests/test_fmv_lookup.py::TestExtractComparablesPrompt -v`

Expected: PASS

**Step 3: Run full test suite to check for regressions**

Run: `poetry run --directory backend pytest backend/tests/test_fmv_lookup.py -v`

Expected: All tests pass

**Step 4: Commit implementation (green)**

```bash
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-abebooks-fmv add backend/app/services/fmv_lookup.py
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-abebooks-fmv commit -m "feat: Add source-specific prompt text for eBay vs AbeBooks"
```

---

### Task 3: Add Test for AbeBooks Context-Aware Query

**Files:**

- Modify: `backend/tests/test_fmv_lookup.py`

**Step 1: Write the failing test**

Add to `test_fmv_lookup.py`:

```python
class TestAbeBooksContextAwareQuery:
    """Tests for AbeBooks context-aware query building."""

    def test_abebooks_includes_volumes_in_query(self):
        """AbeBooks query includes volume count for multi-volume sets."""
        from app.services.fmv_lookup import lookup_abebooks_comparables
        import urllib.parse

        # We can't easily test the full function without mocking HTTP
        # So we test the query building by checking what URL would be generated
        from app.services.fmv_lookup import _build_context_aware_query

        result = _build_context_aware_query(
            title="Life of Scott",
            author="Lockhart",
            volumes=7,
        )
        decoded = urllib.parse.unquote_plus(result).lower()
        assert "7 volumes" in decoded or "7 vol" in decoded
```

**Step 2: Run test to verify it passes (this should already pass)**

Run: `poetry run --directory backend pytest backend/tests/test_fmv_lookup.py::TestAbeBooksContextAwareQuery -v`

Expected: PASS (the query builder already works, we just need to wire it up)

**Step 3: Commit test**

```bash
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-abebooks-fmv add backend/tests/test_fmv_lookup.py
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-abebooks-fmv commit -m "test: Add test for AbeBooks context-aware query"
```

---

### Task 4: Update AbeBooks Function Signature

**Files:**

- Modify: `backend/app/services/fmv_lookup.py:646-673`

**Step 1: Update `lookup_abebooks_comparables()` signature and implementation**

Change from:

```python
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
```

To:

```python
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
```

**Step 2: Run tests to verify no regressions**

Run: `poetry run --directory backend pytest backend/tests/test_fmv_lookup.py -v`

Expected: All tests pass

**Step 3: Commit implementation**

```bash
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-abebooks-fmv add backend/app/services/fmv_lookup.py
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-abebooks-fmv commit -m "feat: Add context-aware query parameters to lookup_abebooks_comparables"
```

---

### Task 5: Update lookup_fmv() Caller

**Files:**

- Modify: `backend/app/services/fmv_lookup.py:714-715`

**Step 1: Update the call to `lookup_abebooks_comparables()`**

Change from:

```python
    # AbeBooks still uses simple query for now
    abebooks = lookup_abebooks_comparables(title, author, max_per_source)
```

To:

```python
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
```

**Step 2: Run full test suite**

Run: `poetry run --directory backend pytest backend/tests/test_fmv_lookup.py -v`

Expected: All tests pass

**Step 3: Run linting**

Run: `poetry run --directory backend ruff check backend/app/services/fmv_lookup.py`

Expected: No errors

**Step 4: Commit implementation**

```bash
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-abebooks-fmv add backend/app/services/fmv_lookup.py
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-abebooks-fmv commit -m "feat: Pass context-aware parameters to AbeBooks lookup"
```

---

### Task 6: Add Integration Test (Optional)

**Files:**

- Modify: `backend/tests/test_fmv_lookup.py`

**Step 1: Add integration test with mocked HTTP**

```python
class TestLookupFmvIntegration:
    """Integration tests for full FMV lookup flow."""

    @patch("app.services.fmv_lookup._fetch_listings_via_scraper_lambda")
    @patch("app.services.fmv_lookup._fetch_search_page")
    @patch("app.services.fmv_lookup._filter_listings_with_claude")
    @patch("app.services.fmv_lookup._extract_comparables_with_claude")
    def test_abebooks_receives_context_aware_params(
        self, mock_extract, mock_filter, mock_fetch_page, mock_fetch_lambda
    ):
        """AbeBooks lookup receives volume and binding parameters."""
        from app.services.fmv_lookup import lookup_fmv

        # Mock eBay (scraper Lambda)
        mock_fetch_lambda.return_value = []
        mock_filter.return_value = []

        # Mock AbeBooks (direct HTTP)
        mock_fetch_page.return_value = "<html>test</html>"
        mock_extract.return_value = []

        lookup_fmv(
            title="Life of Scott",
            author="Lockhart",
            volumes=7,
            binding_type="Full calf",
        )

        # Verify AbeBooks fetch was called
        assert mock_fetch_page.called
        # Check the URL contains context-aware terms
        call_url = mock_fetch_page.call_args[0][0]
        assert "7" in call_url and "volume" in call_url.lower()
```

**Step 2: Run test**

Run: `poetry run --directory backend pytest backend/tests/test_fmv_lookup.py::TestLookupFmvIntegration -v`

Expected: PASS

**Step 3: Commit test**

```bash
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-abebooks-fmv add backend/tests/test_fmv_lookup.py
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-abebooks-fmv commit -m "test: Add integration test for AbeBooks context-aware params"
```

---

### Task 7: Final Validation and PR

**Step 1: Run full test suite**

Run: `poetry run --directory backend pytest backend/tests -v --tb=short`

Expected: 371+ passed (may have 1 pre-existing failure in test_bedrock.py)

**Step 2: Run linting and formatting**

Run: `poetry run --directory backend ruff check backend/`
Run: `poetry run --directory backend ruff format --check backend/`

Expected: No errors

**Step 3: Push branch and create PR**

```bash
git -C /Users/mark/projects/bluemoxon/.worktrees/fix-abebooks-fmv push -u origin fix/abebooks-fmv-parity
```

Create PR:

```bash
gh pr create --repo markthebest12/bluemoxon --base staging --head fix/abebooks-fmv-parity --title "fix: AbeBooks FMV parity with context-aware queries (#379)" --body "## Summary
- Fix prompt to say 'active listings' instead of 'sold listings' for AbeBooks
- Add context-aware query support (volumes, binding, binder, edition)
- AbeBooks now matches eBay's implementation

## Test Plan
- [x] Unit tests for source-specific prompts
- [x] Integration test for context-aware params
- [ ] Manual validation in staging (trigger runbook for multi-volume book)

Closes #379"
```

**Step 4: Watch CI**

Run: `gh pr checks <pr-number> --watch`

Expected: All checks pass

---

## Summary

| Task | Description | Estimated |
|------|-------------|-----------|
| 1 | Add test for source-specific prompt | 3 min |
| 2 | Implement source-specific prompt | 3 min |
| 3 | Add test for AbeBooks context query | 2 min |
| 4 | Update AbeBooks function signature | 3 min |
| 5 | Update lookup_fmv() caller | 2 min |
| 6 | Add integration test | 3 min |
| 7 | Final validation and PR | 5 min |

**Total: ~21 minutes**
