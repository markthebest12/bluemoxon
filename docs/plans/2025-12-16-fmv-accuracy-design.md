# FMV Accuracy Design - Context-Aware Comparable Search

**Date:** 2025-12-16
**Issue:** #384
**Status:** APPROVED

---

## Problem

FMV lookup returns irrelevant comparables because the search query lacks context. For a 7-volume Lockhart "Life of Scott" set worth ~$1,200, the search returned single volumes at $11-$125.

**Root cause:** `_build_search_query()` only uses title keywords + author last name. It does NOT include:

- Volume count (critical for sets)
- Binding type (full calf vs cloth)
- Edition info (first edition)
- Binder attribution

---

## Solution Overview

Pass full book metadata to FMV lookup, build context-aware search queries, and use Claude to filter results by relevance tier.

### Data Flow

```text
Book metadata (title, author, volumes, binding_type, edition, binder, condition)
    |
    v
Template-based query builder (adds "7 volumes", "full calf", "first edition")
    |
    v
Scraper Lambda (JavaScript extracts ~20 listings)
    |
    v
Claude filtering (compares each listing against target book metadata)
    |
    v
Tiered results: high/medium/low relevance
    |
    v
FMV calculation (weights by relevance tier)
```

---

## Section 1: Template-Based Query Builder

Constructs eBay search string from book metadata.

### Base Query

- First 4-5 significant words from title (skip "the", "a", "of")
- Author last name

### Conditional Additions

| If metadata has... | Add to query |
|-------------------|--------------|
| `volumes > 1` | `"{n} volumes"` or `"complete set"` |
| `binding_type` contains "morocco" | `"morocco"` |
| `binding_type` contains "calf" | `"calf binding"` |
| `binding_type` contains "vellum" | `"vellum"` |
| `binder` is set (Riviere, Zaehnsdorf, etc.) | binder name |
| `edition` contains "first" | `"first edition"` |

### Example Transformation

**Input metadata:**

```text
title: "Memoirs of the Life of Sir Walter Scott"
author: "John Gibson Lockhart"
volumes: 7
binding_type: "Full polished calf"
edition: "First Edition"
binder: "J. Leighton"
```

**Generated query:**

```text
memoirs life walter scott lockhart 7 volumes calf binding first edition
```

### Fallback Trigger

If first search returns <3 listings with price data, try simplified query (title + author only) to cast wider net, then rely more heavily on Claude filtering.

---

## Section 2: Claude Filtering Prompt

After JavaScript extracts ~20 raw listings, send to Claude with this structure:

```text
Target book:
- Title: {title}
- Author: {author}
- Volumes: {volumes}
- Binding: {binding_type}
- Binder: {binder}
- Edition: {edition}

Extracted listings:
[{title, price, url, condition, sold_date}, ...]

Task: Rate each listing's relevance as "high", "medium", or "low":
- HIGH: Same work, matching volume count (+-1), similar binding quality
- MEDIUM: Same work, different format (e.g., fewer volumes, lesser binding)
- LOW: Different work, or single volume from a set

Return JSON array with relevance added to each listing.
Only include listings rated "high" or "medium".
```

---

## Section 3: FMV Calculation with Tiered Weighting

### Weighting Rules

- HIGH relevance: weight = 1.0 (full influence)
- MEDIUM relevance: weight = 0.5 (half influence)
- LOW relevance: excluded from calculation

### Calculation Method

1. Separate listings by relevance tier
2. If >= 2 HIGH listings exist: use only HIGH for FMV range
3. If < 2 HIGH but >= 3 MEDIUM: use MEDIUM, note lower confidence
4. If insufficient data: return `fmv_notes: "Insufficient comparable data"` with no range

### FMV Range from Weighted Set

- `fmv_low`: 25th percentile of weighted prices
- `fmv_high`: 75th percentile of weighted prices
- `fmv_confidence`: "high" (>= 3 HIGH), "medium" (>= 3 MEDIUM), "low" (sparse data)

### Example

| Listing | Price | Relevance | Included |
|---------|-------|-----------|----------|
| 7-vol calf set | $1,100 | HIGH | Yes |
| 7-vol morocco set | $1,400 | HIGH | Yes |
| 5-vol cloth | $350 | MEDIUM | Only if needed |
| Single vol | $45 | LOW | No |

**Result:** `fmv_low: $1,100, fmv_high: $1,400, fmv_confidence: "high"`

---

## Section 4: Code Changes Required

### Files to Modify

| File | Changes |
|------|---------|
| `backend/app/services/fmv_lookup.py` | New `_build_context_aware_query()`, new `_filter_listings_with_claude()`, update `lookup_ebay_comparables()` signature |
| `backend/app/api/v1/endpoints/eval_runbook.py` | Pass full book metadata to FMV lookup instead of just title/author |
| `backend/app/schemas/eval_runbook.py` | Add `fmv_confidence` field to response |

### Function Signature Change

```python
# Before
def lookup_ebay_comparables(title: str, author: str | None = None, max_results: int = 5)

# After
def lookup_ebay_comparables(
    title: str,
    author: str | None = None,
    volumes: int = 1,
    binding_type: str | None = None,
    binder: str | None = None,
    edition: str | None = None,
    max_results: int = 5,
)
```

### New Functions

- `_build_context_aware_query(title, author, volumes, binding_type, binder, edition) -> str`
- `_filter_listings_with_claude(listings, book_metadata) -> list[dict]`
- `_calculate_weighted_fmv(listings) -> dict` (with confidence level)

### No Changes to Scraper

JavaScript extraction already returns what we need (title, price, url, condition, sold_date).

---

## Acceptance Criteria

- [ ] Multi-volume sets search includes volume count
- [ ] Search differentiates complete sets from single volumes
- [ ] Premium bindings search includes binding terms
- [ ] Claude filters results by relevance tier (high/medium/low)
- [ ] FMV calculation weights by relevance tier
- [ ] Response includes `fmv_confidence` field
- [ ] Fallback to simplified query when initial search returns <3 results
