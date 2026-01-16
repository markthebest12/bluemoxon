# Analysis Enrichment Implementation Plan

**GitHub Issue:** [#237](https://github.com/markthebest12/bluemoxon/issues/237)
**Design Document:** [2025-12-13-analysis-enrichment-design.md](./2025-12-13-analysis-enrichment-design.md)
**Branch:** `feature/analysis-enrichment` (create via worktree)
**Created:** 2025-12-13

## Goal

Improve book scoring by implementing binder tier bonuses and analysis enrichments.

### Exemplar Book (Production): Book 489

- **Title:** A Short History of the English People
- **Publisher:** Macmillan and Co. (TIER_1) ✅
- **Binder:** Zaehnsdorf (TIER_1) - but tier bonus not applied ❌
- **Current scores:** investment_grade=0, strategic_fit=70, collection_impact=30, overall_score=100
- **Expected after Phase 1-2:** strategic_fit ~125 (+40 +15 DOUBLE), overall_score ~155
- **Expected after ALL phases:** overall_score ~215

### Underdog Book (Staging): Book 502

- **Title:** History of The English People
- **Publisher:** Chapman & Hall (TIER_1) ✅
- **Binder:** Zaehnsdorf (TIER_1) - but tier bonus not applied ❌
- **Current scores:** investment_grade=0, strategic_fit=115, collection_impact=30, overall_score=145
- **Expected after Phase 1-2:** strategic_fit ~170 (+40 +15 DOUBLE), overall_score ~200

**Production exemplar:** <https://app.bluemoxon.com/books/489>
**Staging test book:** <https://staging.app.bluemoxon.com/books/502>

6-phase enrichment:

1. Binder tier scoring
2. Scoring enhancements
3. Prompt improvements
4. Parser enhancements
5. Field extraction improvements
6. Bulk re-analysis

## Current State Assessment (2025-12-13)

### Phase 1: Binder Tier Migration - 95% COMPLETE

**What exists:**

- ✅ `binders.tier` column added (VARCHAR(20))
- ✅ Migration SQL in `health.py` populates TIER_1/TIER_2 values
- ✅ `BinderResponse` schema includes `tier: str | None`
- ✅ Migration ran successfully on staging

**What's missing:**

- ❌ `binders.py:list_binders()` doesn't return `tier` field (line 18-27)
- ❌ `binders.py:get_binder()` doesn't return `tier` field (line 37-53)
- ❌ Need to verify data populated correctly

**Evidence:**

```bash
# Migration ran successfully
curl -X POST https://staging.api.bluemoxon.com/api/v1/health/migrate
# Returns: {"status":"success",...}

# But API doesn't return tier
bmx-api GET /binders
# Returns: [{"id":3,"name":"Sangorski",...}]  # No tier field!
```

### Phase 2: Scoring Enhancement - 100% CODE COMPLETE

**What exists:**

- ✅ `scoring.py:calculate_strategic_fit()` has `binder_tier` parameter
- ✅ TIER_1 (+40) and TIER_2 (+20) scoring implemented
- ✅ DOUBLE TIER 1 bonus (+15) implemented
- ✅ `books.py` passes `binder_tier=book.binder.tier` to scoring

**What's needed:**

- ⏳ Scores need recalculation after Phase 1 API fix
- ⏳ Validate scoring works with test cases

**Evidence:**

```python
# backend/app/services/scoring.py lines 45-51
if binder_tier == "TIER_1":
    score += 40
elif binder_tier == "TIER_2":
    score += 20

if publisher_tier == "TIER_1" and binder_tier == "TIER_1":
    score += 15  # DOUBLE TIER 1 bonus
```

### Phases 3-6: NOT STARTED

These phases require design decisions and new implementation.

---

## Implementation Tasks

### Task 1.1: Fix Binders API to Return Tier (BLOCKING)

**File:** `backend/app/api/v1/binders.py`
**Priority:** HIGH - Blocks all subsequent work

**Current code (line 18-27):**

```python
@router.get("")
def list_binders(db: Session = Depends(get_db)):
    """List all authenticated binding houses."""
    binders = db.query(Binder).order_by(Binder.name).all()
    return [
        {
            "id": b.id,
            "name": b.name,
            "full_name": b.full_name,
            "authentication_markers": b.authentication_markers,
            "book_count": len(b.books),
        }
        for b in binders
    ]
```

**Change to:**

```python
@router.get("")
def list_binders(db: Session = Depends(get_db)):
    """List all authenticated binding houses."""
    binders = db.query(Binder).order_by(Binder.name).all()
    return [
        {
            "id": b.id,
            "name": b.name,
            "full_name": b.full_name,
            "authentication_markers": b.authentication_markers,
            "tier": b.tier,  # ADD THIS LINE
            "book_count": len(b.books),
        }
        for b in binders
    ]
```

**Also fix `get_binder()` (line 37-53):**

```python
return {
    "id": binder.id,
    "name": binder.name,
    "full_name": binder.full_name,
    "authentication_markers": binder.authentication_markers,
    "tier": binder.tier,  # ADD THIS LINE
    "book_count": len(binder.books),
    "books": [...]
}
```

**Test:**

```bash
bmx-api GET /binders | jq '.[0]'
# Should include: "tier": "TIER_1" or "TIER_2" or null
```

---

### Task 1.2: Verify Binder Tier Data

After API fix, verify data is correct:

```bash
# Check TIER_1 binders
bmx-api GET /binders | jq '.[] | select(.tier == "TIER_1") | .name'
# Expected: Zaehnsdorf, Rivière, Sangorski, etc.

# Check TIER_2 binders
bmx-api GET /binders | jq '.[] | select(.tier == "TIER_2") | .name'
# Expected: Bayntun, Morrell, Root & Son, etc.
```

**If data missing, run migration:**

```bash
curl -X POST https://staging.api.bluemoxon.com/api/v1/health/migrate
```

---

### Task 2.1: Recalculate All Book Scores

After Phase 1 complete, trigger score recalculation:

**Option A: Via API (if endpoint exists)**

```bash
bmx-api POST /books/recalculate-scores
```

**Option B: Update any book to trigger recalc**

```bash
# Touch a book to trigger score recalculation
bmx-api PATCH /books/21 '{"notes": "Score recalc trigger"}'
```

**Option C: Bulk recalc via direct call (if needed)**
Add to `health.py` a recalculate-all endpoint.

---

### Task 2.2: Validate Scoring Test Cases

**Test Case 1: Book 21 (Sangorski + Macmillan TIER_1)**

Before fix:

- `strategic_fit: 85`

Expected after fix (manual calculation):

- Base: 30
- Publisher TIER_1: +35 → 65
- Binder TIER_1: +40 → 105
- DOUBLE TIER 1: +15 → 120
- Complete: +15 → 135
- Pre-1900 (1894): +15 → 150
- Strategic fit should be ~150

**Test Case 2: Book 396 (Zaehnsdorf, no TIER_1 publisher)**

Before fix:

- `strategic_fit: 60`

Expected after fix:

- Binder TIER_1: +40 bonus
- Should increase to ~100

**Test Case 3: Book 404 (Chapman & Hall TIER_1, no authenticated binder)**

- Should remain unchanged (no binder tier bonus)

---

### Phase 3: Prompt Enhancement (NOT STARTED)

**Design needed:** What specific prompt improvements?

- Reference design doc Section 3 for requirements
- Add binder context to analysis prompts
- Include tier information in enrichment

**Files to modify:**

- `backend/app/services/analysis.py` - prompt templates
- `backend/app/services/prompts/` - if prompt directory exists

---

### Phase 4: Parser Enhancement (NOT STARTED)

**ROOT CAUSE IDENTIFIED (2025-12-13):** Parser regex doesn't match actual LLM output format.

**Current parser regex (markdown_parser.py:163-165):**

```python
low_match = re.search(r"Low\s*\|?\s*\$?([\d,]+)", text)
mid_match = re.search(r"Mid\s*\|?\s*\$?([\d,]+)", text)
high_match = re.search(r"High\s*\|?\s*\$?([\d,]+)", text)
```

**Expects:** `Low | $450` or `Mid | $550`

**Actual LLM output:**

- `"Current Fair Market Value: $700-900"`
- `"Fair Market Value | $550-$650 (with provenance premium)"`
- `"Insurance valuation: $800-1,000"`

**Fix options:**

1. **Prompt engineering (Phase 3):** Force LLM to output structured table format
2. **Parser improvement:** Add regex patterns for range formats like `\$?([\d,]+)\s*[-–]\s*\$?([\d,]+)`
3. **Structured output:** Use Claude's JSON mode for analysis generation

**Files to modify:**

- `backend/app/utils/markdown_parser.py` - improve `_parse_market_analysis()` regex

---

### Phase 5: Field Extraction (NOT STARTED)

**ROOT CAUSE IDENTIFIED (2025-12-13):** This is the primary cause of scoring mismatch between book 489 (prod exemplar) and book 502 (staging underdog).

**Code Gap:** Analysis parsing extracts `condition_grade` into `parsed.condition_assessment["condition_grade"]` (markdown_parser.py:127), but the API endpoints (`put_book_analysis`, `upload_analysis_for_book`) **never copy this to `book.condition_grade`**.

**Fields missing from analysis → book extraction:**

| Field | Parser Output | Book Field | Impact |
|-------|---------------|------------|--------|
| `condition_grade` | `parsed.condition_assessment["condition_grade"]` | `book.condition_grade` | -15 strategic_fit |
| `value_low/mid/high` | `parsed.market_analysis["valuation"]` | `book.value_*` | -5 investment_grade (but parser regex also broken - Phase 4) |
| `provenance` | Not extracted | `book.provenance` | Display only |
| `notes` | Not extracted | `book.notes` | Display only |

**Files to modify:**

- `backend/app/api/v1/books.py` - add extraction code after line 1028 (put_book_analysis) and line 1214 (upload_analysis_for_book):

  ```python
  # Extract condition_grade from analysis
  if parsed.condition_assessment and "condition_grade" in parsed.condition_assessment:
      book.condition_grade = parsed.condition_assessment["condition_grade"]
  ```

---

### Phase 6: Bulk Re-analysis (NOT STARTED)

**Design needed:** Strategy for re-analyzing existing books

- Queue system for batch processing
- Rate limiting for API costs
- Progress tracking

---

## Validation Checklist

### Phase 1 Complete When

- [ ] `GET /binders` returns `tier` field for all binders
- [ ] TIER_1 binders: Zaehnsdorf, Rivière, Sangorski, etc.
- [ ] TIER_2 binders: Bayntun, Morrell, etc.

### Phase 2 Complete When

- [ ] Book 502 (staging underdog) strategic_fit increases from 115 to ~170
- [ ] Book 502 overall_score increases from 145 to ~200
- [ ] Book 21 (Coridons Song - Sangorski+Macmillan) gets DOUBLE TIER 1 bonus
- [ ] Book 396 (Ariadne - Zaehnsdorf only) strategic_fit increases from 60 to ~100
- [ ] Books without premium binders unchanged

### Full Feature Complete When

- [ ] Book 489 (prod exemplar) reaches ~215 overall_score after all phases
- [ ] Book 502 (staging underdog) reaches ~200+ overall_score after Phase 1-2
- [ ] All phases validated
- [ ] Documentation updated

---

## For Future Claude Sessions

### Starting This Work

```
## Task
Continue Analysis Enrichment implementation (#237), Phase 1 Task 1.1

## References
- GitHub Issue: #237
- Design Doc: docs/plans/2025-12-13-analysis-enrichment-design.md
- Implementation Doc: docs/plans/2025-12-13-analysis-enrichment-implementation.md

## Current State
- Phase: 1 of 6, Task 1.1
- Last completed: Created implementation plan
- Issue: binders.py doesn't return tier field

## Expected Outcome
- [ ] Edit binders.py to include tier in responses
- [ ] Deploy to staging
- [ ] Verify: bmx-api GET /binders shows tier values

## Constraints
- Small, surgical change - just add tier field to two endpoints
- Run tests before deploying
```

### Checking Progress

```bash
# Quick state check
bmx-api GET /binders | jq '.[0]'  # Should show tier
bmx-api GET /books/21 | jq '.strategic_fit'  # Should be ~150 after fix
gh issue view 237  # Check issue status
```

---

## Appendix: Key File Locations

| Component | File | Line Numbers |
|-----------|------|--------------|
| Binder model | `backend/app/models/binder.py` | tier field defined |
| Binder API | `backend/app/api/v1/binders.py` | 18-27, 37-53 |
| Binder schema | `backend/app/schemas/reference.py` | BinderResponse |
| Scoring logic | `backend/app/services/scoring.py` | 45-51 (binder tier) |
| Books API | `backend/app/api/v1/books.py` | passes binder_tier |
| Migration | `backend/app/api/v1/health.py` | MIGRATION_I0123456ABCD_SQL |
