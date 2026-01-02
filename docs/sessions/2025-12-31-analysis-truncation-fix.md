# Session: Analysis Truncation Fix and Batch Re-Analysis

**Date:** 2025-12-31 / 2026-01-01
**Issue:** 143 Napoleon analyses silently truncated (missing Conclusions and Recommendations sections)
**Status:** COMPLETE - All high-image books fixed

---

## CRITICAL SESSION RULES (READ FIRST)

### 1. ALWAYS USE SUPERPOWERS SKILLS
**MANDATORY:** Invoke relevant skills BEFORE any response or action. Even 1% chance = invoke the skill.

**Key skills for this work:**
- `superpowers:brainstorming` - Before creative/feature work (design phase)
- `superpowers:writing-plans` - Before implementation (creates detailed step-by-step plan)
- `superpowers:executing-plans` - When implementing from a plan doc
- `superpowers:subagent-driven-development` - Alternative execution with fresh subagent per task
- `superpowers:receiving-code-review` - Before implementing review feedback
- `superpowers:verification-before-completion` - Before claiming work is done
- `superpowers:systematic-debugging` - Before proposing bug fixes

**IF A SKILL APPLIES, YOU MUST USE IT. This is not optional.**

**For GH #743 implementation:** Use `superpowers:writing-plans` first to create detailed plan, then execute with chosen method.

### 2. BASH COMMAND RULES - NEVER USE (triggers permission prompts):
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings (corrupts passwords)

### 3. BASH COMMAND RULES - ALWAYS USE:
- Simple single-line commands
- Separate sequential Bash tool calls instead of &&
- `bmx-api` for all BlueMoxon API calls (no permission prompts)

---

## Progress Summary (2026-01-01 16:55 UTC)

### Successfully Fixed This Session
| Book | Images | Resized To | Status |
|------|--------|------------|--------|
| 60   | 16     | 1200px     | SUCCESS - `analysis_issues: null` |
| 51   | 12     | 1600px     | SUCCESS - `analysis_issues: null` |
| 18   | 18     | 1200px     | SUCCESS - `analysis_issues: null` |
| 67   | 18     | 800px      | SUCCESS - `analysis_issues: null` |
| 66   | 20     | 800px      | SUCCESS - `analysis_issues: null` |
| 489  | 20     | 800px      | SUCCESS - `analysis_issues: null` |
| 65   | 18     | 800px      | SUCCESS - `analysis_issues: null` |
| 53   | 12     | 800px      | SUCCESS - `analysis_issues: null` |

### Follow-up Improvements
See GitHub issue #743 for improvements identified during this session:
1. Change default model to Opus (both sync and async endpoints)
2. Improve error messages for image size issues
3. Fix warning icon hover tooltip (replace HTML title with Vue tooltip)
4. Auto-cleanup stale jobs on re-trigger
5. Document image resize thresholds in ops runbook

### Timeout Books (Different Issue - Not Addressed Yet)
- 22, 339, 400, 48, 337 (5 books)
- These need investigation - may be complex analyses exceeding 15-min Lambda timeout

---

## Key Findings: Image Resize Thresholds

### CONFIRMED WORKING THRESHOLDS
| Max Dimension | Max Images | Notes |
|---------------|------------|-------|
| 1600px        | 12         | Book 51 worked |
| 1200px        | 16-18      | Books 60, 18 worked |
| 800px         | 18-20      | Books 67, 66, 489, 65 all worked |

### ROOT CAUSE DISCOVERY
The issue is NOT just pixel count - it's **base64 payload size**:
- Book 18 (worked @ 1200px): Images 120-424KB each
- Book 67 (failed @ 1200px): Images 675KB-1.8MB each

High-quality JPEGs with large file sizes create massive base64 payloads that exceed Bedrock's input limit, even at same pixel dimensions.

### SOLUTION: 800px is the safe floor
- User specified: **Do not go lower than 800px**
- 800px works reliably for 18-20 images regardless of JPEG quality

---

## Next Steps: Implement GH #743

**Issue:** https://github.com/markthebest12/bluemoxon/issues/743

### Status: NEEDS MORE DETAIL BEFORE EXECUTION

The issue needs these decisions/details added:

1. **Tooltip (Item 3):** No Vue tooltip library exists. Decision needed:
   - Option A: Add `floating-vue` dependency (~8KB)
   - Option B: Build simple custom CSS tooltip (no dependency)
   - Option C: Skip this improvement for now

2. **Error messages (Item 2):** Need to trace exact error path:
   - `bedrock.py` throws exception → `worker.py:324` stores `str(e)[:1000]` as `job.error_message`
   - Need to identify WHERE to catch Bedrock's "Input is too long" and add image count/size context

### Before Starting Implementation

1. Use `superpowers:writing-plans` to create detailed implementation plan
2. Add missing details to GH #743 or create separate plan doc
3. Use `superpowers:executing-plans` or `superpowers:subagent-driven-development` for execution

---

## Background

124 Napoleon analyses were silently truncated because `max_tokens=16000` was insufficient for 12+ section analyses. The final sections (Conclusions and Recommendations) were cut off. Count increased to 143 during verification.

## Root Cause

Bedrock `max_tokens` parameter set too low (16000) for comprehensive 12-section Napoleon analyses.

## Solution Implemented

### PR #737 - Analysis Truncation Fix (merged to main)
1. **bedrock.py:409** - Changed `max_tokens` from 16000 to 32000
2. **bedrock.py:463-469** - Added `stop_reason` logging to detect truncation
3. **book.py schema** - Added `analysis_issues: list[str] | None` field
4. **books.py** - Added `_get_analysis_issues()` helper function
5. **Frontend** - Added `AnalysisIssuesWarning.vue` component

### PR #740 - Metadata Block Stripping (merged to main)
- Fixed `strip_structured_data()` to also strip `## 14. Metadata Block` section

### PR #741 - Case-Insensitive Metadata Stripping (merged to main)
- P0 code review fix: Made metadata block stripping case-insensitive
- Uses regex with `IGNORECASE` flag

---

## Batch Re-Analysis Results

### Final Summary
| Metric | Count |
|--------|-------|
| Original truncated | 143 |
| Fixed via batch re-analysis | 126+ |
| Fixed via image resize (800px) | 8 |
| Remaining | 0 |
| Timeout issues (separate problem) | 5 |

**All high-image books now have `analysis_issues: null`.**

---

## Image Resize Workflow Reference

**For each book needing resize:**

### Step 1: Create temp directory
```bash
mkdir -p .tmp/book{BOOK_ID}
```

### Step 2: Get image S3 keys
```bash
bmx-api --prod GET "/books/{BOOK_ID}/images" | jq -r '.[].s3_key'
```

### Step 3: Download images (bulk)
```bash
AWS_PROFILE=bmx-prod aws s3 cp s3://bluemoxon-images/books/ .tmp/book{BOOK_ID}/ --recursive --exclude "*" --include "{BOOK_ID}_*.jpeg"
```

### Step 4: Resize all images to 800px max
```bash
sips --resampleHeightWidthMax 800 .tmp/book{BOOK_ID}/*.jpeg
```

### Step 5: Upload back to S3 (bulk)
```bash
AWS_PROFILE=bmx-prod aws s3 cp .tmp/book{BOOK_ID}/ s3://bluemoxon-images/books/ --recursive --exclude "*" --include "{BOOK_ID}_*.jpeg"
```

### Step 6: Trigger re-analysis
```bash
bmx-api --prod POST "/books/{BOOK_ID}/analysis/generate-async" '{"model": "opus"}'
```

### Step 7: Verify success
```bash
bmx-api --prod GET "/books/{BOOK_ID}" | jq '{id, analysis_issues}'
```

---

## Files Modified

### Backend
- `backend/app/api/v1/books.py` - Added `_get_analysis_issues()` helper
- `backend/app/schemas/book.py` - Added `analysis_issues` field
- `backend/app/services/bedrock.py` - Increased max_tokens, added stop_reason logging
- `backend/app/utils/markdown_parser.py` - Fixed metadata block stripping (case-insensitive regex)
- `backend/tests/test_markdown_parser.py` - Added 7 tests for strip_structured_data
- `backend/tests/test_books.py` - Added TestGetAnalysisIssues class (7 tests)

### Frontend
- `frontend/src/composables/useFormatters.ts` - Added `formatAnalysisIssues`
- `frontend/src/components/AnalysisIssuesWarning.vue` - New component
- `frontend/src/stores/books.ts` - Added analysis_issues to interface
- `frontend/src/stores/acquisitions.ts` - Added analysis_issues to interface
- `frontend/src/views/AcquisitionsView.vue` - Using new component
- `frontend/src/views/BookDetailView.vue` - Using new component
