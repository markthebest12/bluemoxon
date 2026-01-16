# Parser Metadata Stripping Improvements

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make metadata block stripping more robust by fixing truncation behavior, adding defensive tests, and improving logging/documentation.

**Architecture:** Improve `strip_structured_data()` in markdown_parser.py to strip only the metadata section (not truncate to end), add defensive tests for edge cases, and add debug logging for observability.

**Tech Stack:** Python, pytest, regex

**Background:** PR #740 and #741 fixed the critical P0 (hardcoded section number) and P3 (case-sensitivity) issues. This plan addresses the remaining P1-P3 issues from the code review.

---

## Task 1: Fix Metadata Block Truncation Behavior

**Problem:** Current implementation truncates everything from "## N. Metadata Block" to end of document. If Claude ever outputs content after metadata (e.g., an Appendix), that content is silently lost.

**Files:**

- Modify: `backend/app/utils/markdown_parser.py:198-222`
- Test: `backend/tests/test_markdown_parser.py`

### Step 1: Write failing test for metadata in middle of document

Add test that has content AFTER the metadata block:

```python
def test_preserves_content_after_metadata_block(self):
    """Test that content after metadata block is preserved (P1 fix).

    Napoleon prompt says metadata MUST be last, but we should be defensive
    in case Claude outputs content after it.
    """
    markdown = """## 13. Conclusions

Good acquisition.

## 14. Metadata Block

CONDITION_GRADE: VG+
VALUATION_MID: 300

## 15. Appendix

Additional notes about provenance.
"""
    result = strip_structured_data(markdown)
    assert "## 14. Metadata Block" not in result
    assert "CONDITION_GRADE" not in result
    assert "## 13. Conclusions" in result
    assert "## 15. Appendix" in result  # Content after should be preserved
    assert "Additional notes about provenance" in result
```

### Step 2: Run test to verify it fails

Run: `poetry run pytest backend/tests/test_markdown_parser.py::TestStripStructuredData::test_preserves_content_after_metadata_block -v`

Expected: FAIL - "## 15. Appendix" not in result (current truncation removes it)

### Step 3: Update regex to strip only metadata section

Change the regex from truncation (`.*`) to bounded stripping (stop at next section header or end):

```python
def strip_structured_data(markdown: str) -> str:
    """Remove the structured data block from markdown for display.

    Strips two formats:
    1. Explicit markers:
       ---STRUCTURED-DATA---
       ...
       ---END-STRUCTURED-DATA---

    2. Metadata Block section header (Napoleon v2 format):
       ## N. Metadata Block
       ...
       (content up to next ## header or end of document)

    Note: STRUCTURED-DATA markers are stripped first, then Metadata Block.
    Both formats may be present in legacy analyses.
    """
    # Strip explicit STRUCTURED-DATA markers
    pattern = r"---STRUCTURED-DATA---\s*.*?\s*---END-STRUCTURED-DATA---\s*"
    result = re.sub(pattern, "", markdown, flags=re.DOTALL)

    # Strip "## N. Metadata Block" section up to next section header or end
    # Uses non-greedy match and lookahead to preserve content after
    # Pattern: section header, any content, stop at next "## " or end
    metadata_pattern = r"\n*## \d+\.\s*Metadata Block.*?(?=\n## |\Z)"
    result = re.sub(metadata_pattern, "", result, flags=re.DOTALL | re.IGNORECASE)

    return result.strip()
```

### Step 4: Run test to verify it passes

Run: `poetry run pytest backend/tests/test_markdown_parser.py::TestStripStructuredData -v`

Expected: All tests PASS including new test

### Step 5: Commit

```bash
git add backend/app/utils/markdown_parser.py backend/tests/test_markdown_parser.py
git commit -m "fix(parser): preserve content after metadata block section"
```

---

## Task 2: Add Debug Logging to strip_structured_data

**Problem:** `strip_metadata_block()` in analysis_parser.py has logging, but `strip_structured_data()` in markdown_parser.py silently removes content. Debugging production issues is harder without observability.

**Files:**

- Modify: `backend/app/utils/markdown_parser.py:198-222`

### Step 1: Add logger import and debug logging

```python
import logging

logger = logging.getLogger(__name__)

def strip_structured_data(markdown: str) -> str:
    """Remove the structured data block from markdown for display.
    ...docstring unchanged...
    """
    # Strip explicit STRUCTURED-DATA markers
    pattern = r"---STRUCTURED-DATA---\s*.*?\s*---END-STRUCTURED-DATA---\s*"
    result = re.sub(pattern, "", markdown, flags=re.DOTALL)
    if result != markdown:
        logger.debug("Stripped STRUCTURED-DATA markers from markdown")

    # Strip "## N. Metadata Block" section up to next section header or end
    metadata_pattern = r"\n*## \d+\.\s*Metadata Block.*?(?=\n## |\Z)"
    before_metadata_strip = result
    result = re.sub(metadata_pattern, "", result, flags=re.DOTALL | re.IGNORECASE)
    if result != before_metadata_strip:
        logger.debug("Stripped Metadata Block section from markdown")

    return result.strip()
```

### Step 2: Run linter and tests

Run: `poetry run ruff check backend/app/utils/markdown_parser.py`
Run: `poetry run pytest backend/tests/test_markdown_parser.py::TestStripStructuredData -v`

Expected: No lint errors, all tests pass

### Step 3: Commit

```bash
git add backend/app/utils/markdown_parser.py
git commit -m "feat(parser): add debug logging to strip_structured_data"
```

---

## Task 3: Document Metadata Format Differences

**Problem:** There are THREE different metadata strip functions/formats which is confusing:

1. `strip_structured_data()` handles `---STRUCTURED-DATA---` markers and `## N. Metadata Block` sections
2. `strip_metadata_block()` handles `<!-- METADATA_START -->` HTML comment markers

These are for DIFFERENT purposes but documentation doesn't explain when to use each.

**Files:**

- Modify: `backend/app/utils/markdown_parser.py` (docstring update)
- Modify: `backend/app/services/analysis_parser.py` (docstring update)

### Step 1: Update markdown_parser.py docstring

Add module-level docstring explaining the metadata formats:

```python
"""Markdown parser utilities for extracting structured data from AI analysis.

METADATA FORMATS:
This module handles metadata embedded in analysis markdown for DISPLAY purposes.
See analysis_parser.py for metadata EXTRACTION (JSON parsing).

Display stripping formats (strip_structured_data):
1. STRUCTURED-DATA markers (legacy v1): Delimited block with key:value pairs
   ---STRUCTURED-DATA---
   KEY: value
   ---END-STRUCTURED-DATA---

2. Metadata Block section (Napoleon v2): Section header with key:value content
   ## 14. Metadata Block
   KEY: value
   (Note: Section number may vary; stripping is case-insensitive)

Processing order: STRUCTURED-DATA is stripped first, then Metadata Block.
Both may be present in analyses generated during format transitions.
"""
```

### Step 2: Update analysis_parser.py docstring

```python
"""Parser for extracting structured metadata from AI analysis responses.

METADATA EXTRACTION vs DISPLAY STRIPPING:
- This module EXTRACTS metadata as JSON for storage in database fields
- markdown_parser.py STRIPS metadata for display purposes

This module handles HTML comment marker format:
<!-- METADATA_START -->
{"condition_grade": "VG+", "valuation_mid": 300}
<!-- METADATA_END -->

This format allows structured JSON extraction while remaining invisible
in rendered markdown.
"""
```

### Step 3: Run linter

Run: `poetry run ruff check backend/app/utils/markdown_parser.py backend/app/services/analysis_parser.py`

Expected: No errors

### Step 4: Commit

```bash
git add backend/app/utils/markdown_parser.py backend/app/services/analysis_parser.py
git commit -m "docs(parser): document metadata format differences and processing order"
```

---

## Verification

After all tasks complete:

```bash
# Run full test suite for parsers
poetry run pytest backend/tests/test_markdown_parser.py backend/tests/test_analysis_parser.py -v

# Run linter on modified files
poetry run ruff check backend/app/utils/markdown_parser.py backend/app/services/analysis_parser.py
```

---

## Summary of Issues Addressed

| Priority | Issue | Resolution |
|----------|-------|------------|
| P1 | Truncates everything after metadata | Fixed with bounded regex lookahead |
| P1 | No test for metadata NOT at end | Added defensive test |
| P2 | Inconsistent stripping behavior | Fixed - now both use bounded removal |
| P2 | Multiple similar strip functions | Documented - they're for different formats |
| P2 | Order dependency not documented | Added to module docstrings |
| P3 | No logging for stripping | Added debug logging |
