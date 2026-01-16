# Analysis & Acquisition Enrichment Design

**Date:** 2025-12-13
**Status:** Approved
**Problem:** Automated acquisition flow produces lower quality analyses than manual workflow

## Problem Statement

The automated acquisition flow (BMX) produces analysis documents that don't match the exemplar quality from the manual workflow. Comparing book 501 (automated) vs book 489 (manual) for the same J.R. Green title:

| Field | Book 489 (Exemplar) | Book 501 (Automated) |
|-------|---------------------|---------------------|
| `value_mid` | $550 | null |
| `condition_grade` | VG | null |
| `notes` | Populated | null |
| `provenance` | ICAEW prize, Nov 1946 | null |
| `investment_grade` | ~35 | 0 |
| `strategic_fit` | 115+ | 70 |
| `overall_score` | ~215 | 100 |

## Root Causes

1. **Parser format mismatch** - Analysis outputs FMV as "Retail Value Range: $650-$900" but parser expects `| Low | $450 |` table format
2. **Missing binder tier scoring** - Publisher tier exists but binder tier doesn't, missing +40 points for Tier 1 binders
3. **No DOUBLE TIER 1 bonus** - When both publisher AND binder are Tier 1, should add +15 bonus
4. **No field extraction** - Condition grade, provenance, notes aren't extracted from analysis to book record
5. **Prompt lacks image analysis guidance** - Doesn't instruct Claude to look for binder stamps, provenance markers in photos

## Goals

1. **Parity with exemplar** - Book 501 should score and display like book 489
2. **Consistent output** - Every analysis follows the same parseable structure
3. **Data-driven scoring** - Binder tier stored in DB like publisher tier
4. **Field extraction** - Analysis populates book record fields automatically
5. **Retroactive fix** - All 70+ existing books can be re-analyzed

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| `value_mid` populated | null | extracted from analysis |
| `investment_grade` | 0 | ~35 (for 33% discount) |
| `strategic_fit` | 70 | 115+ (with binder tier + DOUBLE TIER 1) |
| `overall_score` | 100 | ~215 |
| `notes`, `provenance` | null | populated from analysis |

---

## Phase 1: Binder Tier Migration

### Data Model Change

Add `tier` field to Binder model, mirroring Publisher:

```python
# backend/app/models/binder.py
class Binder(Base):
    __tablename__ = "binders"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    tier = Column(String(20), nullable=True)  # NEW: TIER_1, TIER_2, or null
    created_at = Column(DateTime, default=func.now())
```

### Migration SQL

```sql
ALTER TABLE binders ADD COLUMN tier VARCHAR(20);

-- Tier 1 Binders (per Victorian Book Acquisition Guide)
UPDATE binders SET tier = 'TIER_1' WHERE name IN (
    'Zaehnsdorf', 'Rivière', 'Riviere', 'Sangorski & Sutcliffe',
    'Bayntun', 'Bayntun-Riviere', 'Hayday'
);

-- Tier 2 Binders
UPDATE binders SET tier = 'TIER_2' WHERE name IN (
    'Bumpus', 'Sotheran', 'Root & Son', 'Morrell'
);
```

### Files Modified

- `backend/alembic/versions/xxx_add_binder_tier.py` - Migration
- `backend/app/models/binder.py` - Add tier field
- `backend/app/schemas/binder.py` - Add tier to schema

---

## Phase 2: Scoring Enhancement

### Changes to `scoring.py`

```python
def calculate_strategic_fit(
    publisher_tier: str | None,
    binder_tier: str | None,        # NEW parameter
    year_start: int | None,
    is_complete: bool,
    condition_grade: str | None,
    author_priority_score: int,
    volume_count: int,              # NEW parameter
) -> int:
    score = 0

    # Publisher tier (existing)
    if publisher_tier == "TIER_1":
        score += 35
    elif publisher_tier == "TIER_2":
        score += 15

    # Binder tier (NEW)
    if binder_tier == "TIER_1":
        score += 40
    elif binder_tier == "TIER_2":
        score += 20

    # DOUBLE TIER 1 bonus (NEW)
    if publisher_tier == "TIER_1" and binder_tier == "TIER_1":
        score += 15

    # Era scoring (existing)
    if year_start and 1800 <= year_start <= 1901:
        score += 20

    # Complete set (existing)
    if is_complete:
        score += 15

    # Condition - add VG to accepted grades (existing logic, expanded)
    if condition_grade in ("Fine", "VG+", "VG", "Very Good", "Good"):
        score += 15

    # Volume penalty - graduated scale (UPDATED)
    if volume_count == 4:
        score -= 10
    elif volume_count >= 5:
        score -= 20

    # Author priority (existing)
    score += author_priority_score

    return score
```

### Score Breakdown for Book 501 (After Fix)

| Component | Points | Reason |
|-----------|--------|--------|
| Publisher TIER_1 | +35 | Chapman & Hall |
| Binder TIER_1 | +40 | Zaehnsdorf |
| DOUBLE TIER 1 | +15 | Both Tier 1 |
| Victorian Era | +20 | 1892 |
| Complete Set | +15 | 4 volumes, all present |
| Condition | +15 | VG (once extracted) |
| 4 Volumes | -10 | Graduated penalty |
| New Author | +30 | First J.R. Green |
| **Strategic Fit** | **160** | (vs current 70) |

### Files Modified

- `backend/app/services/scoring.py` - Add binder_tier, DOUBLE TIER 1, volume penalty
- `backend/app/api/v1/books.py` - Pass binder_tier to scoring functions
- `backend/tests/test_scoring.py` - Add binder tier and DOUBLE TIER 1 tests

---

## Phase 3: Prompt Enhancement

### New Prompt: `napoleon-framework/v2.md`

Add to existing prompt:

#### Image Analysis Instructions (NEW)

```markdown
## Image Analysis Requirements

Carefully examine ALL attached images for:

**Authentication Markers:**
- Binder stamps (typically on front turn-in) - transcribe exact text
- Gilt signatures on spine
- Quality indicators (raised bands, gilt tooling style)

**Provenance Indicators:**
- Bookplates or ownership inscriptions
- Prize labels or presentation inscriptions
- Institutional crests or stamps
- Armorial bindings

Document findings in the Header Block with exact transcriptions.
```

#### Required Parseable Fields (NEW)

```markdown
## Required Output Format

### Header Block (MUST include these exact fields)

**Condition Grade:** [Fine|VG+|VG|VG-|Good+|Good|Fair|Poor]
**Provenance:** [Description or "None identified"]
**Key Notes:** [2-3 key points for book record]

### Fair Market Value (MUST use this exact table format)

| Scenario | Value |
|----------|-------|
| Low | $XXX |
| Mid | $XXX |
| High | $XXX |
```

#### Conditional Sections

```markdown
### DOUBLE TIER 1 Classification (Include IF publisher AND binder are both Tier 1)

If this book has BOTH a Tier 1 publisher AND a Tier 1 binder, include this section
documenting the premium status.

### The Institution (Include IF prize/presentation binding identified)

If provenance indicates institutional origin (prize, presentation, library),
document the institution's history and significance.
```

### Files Modified

- `infrastructure/prompts/napoleon-framework/v2.md` - New prompt version
- `backend/app/services/bedrock.py` - Update PROMPT_KEY to v2

---

## Phase 4: Parser Enhancement

### Multi-Format Valuation Extraction

```python
def _parse_market_analysis(text: str) -> dict:
    result: dict = {"raw_text": text}

    # Format 1: Table format (preferred - from new prompt)
    low_match = re.search(r"Low\s*\|?\s*\$?([\d,]+)", text)
    mid_match = re.search(r"Mid\s*\|?\s*\$?([\d,]+)", text)
    high_match = re.search(r"High\s*\|?\s*\$?([\d,]+)", text)

    # Format 2: Range format (legacy - from old analyses)
    if not (low_match and high_match):
        range_match = re.search(
            r"(?:Retail Value|Value)\s*Range[:\s]*\$?([\d,]+)[–-]\$?([\d,]+)",
            text
        )
        if range_match:
            low_val = int(range_match.group(1).replace(",", ""))
            high_val = int(range_match.group(2).replace(",", ""))
            result["valuation"] = {
                "low": low_val,
                "mid": (low_val + high_val) // 2,
                "high": high_val,
            }
            return result

    # Format 1 extraction
    if low_match or mid_match or high_match:
        result["valuation"] = {}
        if low_match:
            result["valuation"]["low"] = int(low_match.group(1).replace(",", ""))
        if mid_match:
            result["valuation"]["mid"] = int(mid_match.group(1).replace(",", ""))
        if high_match:
            result["valuation"]["high"] = int(high_match.group(1).replace(",", ""))

    return result
```

### Condition Grade Extraction

```python
def _parse_condition_assessment(text: str) -> dict:
    result: dict = {"raw_text": text}

    # Condition grade - multiple formats
    grade_patterns = [
        r"\*\*Condition Grade:\*\*\s*(\w+[\+\-]?)",
        r"\*\*Grade:\*\*\s*(\w+[\+\-]?)",
        r"Condition Grade:\s*(\w+[\+\-]?)",
    ]
    for pattern in grade_patterns:
        match = re.search(pattern, text)
        if match:
            result["condition_grade"] = match.group(1).strip()
            break

    # Binding description
    binding_match = re.search(
        r"\*\*(?:Binding|Type):\*\*\s*(.+?)(?:\n|$)", text
    )
    if binding_match:
        result["binding_type"] = binding_match.group(1).strip()

    return result
```

### Provenance and Notes Extraction

```python
def _extract_provenance(markdown: str) -> str | None:
    match = re.search(r"\*\*Provenance:\*\*\s*(.+?)(?:\n\n|\n\*\*|$)", markdown, re.DOTALL)
    return match.group(1).strip() if match else None

def _extract_notes(markdown: str) -> str | None:
    match = re.search(r"\*\*Key Notes:\*\*\s*(.+?)(?:\n\n|\n\*\*|$)", markdown, re.DOTALL)
    return match.group(1).strip() if match else None
```

### Files Modified

- `backend/app/utils/markdown_parser.py` - Multi-format extraction
- `backend/tests/test_markdown_parser.py` - Parser tests for new formats

---

## Phase 5: Field Extraction

### Worker Enhancement

```python
# backend/app/worker.py - after parse_analysis_markdown()

def extract_book_fields(book: Book, parsed: ParsedAnalysis) -> None:
    """Populate book fields from parsed analysis."""

    # FMV from market_analysis
    valuation = (parsed.market_analysis or {}).get("valuation", {})
    if valuation.get("low"):
        book.value_low = Decimal(str(valuation["low"]))
    if valuation.get("mid"):
        book.value_mid = Decimal(str(valuation["mid"]))
        book.fair_market_value = book.value_mid
        book.fmv_updated_at = datetime.now(UTC)
        book.fmv_source = "ai_analysis"
    if valuation.get("high"):
        book.value_high = Decimal(str(valuation["high"]))

    # Condition from condition_assessment
    condition = parsed.condition_assessment or {}
    if condition.get("condition_grade"):
        book.condition_grade = normalize_condition_grade(condition["condition_grade"])
    if condition.get("binding_type"):
        book.binding_description = condition["binding_type"]

    # Provenance and notes
    if parsed.provenance:
        book.provenance = parsed.provenance
    if parsed.notes:
        book.notes = parsed.notes
```

### Condition Grade Normalization

```python
def normalize_condition_grade(grade: str) -> str:
    """Normalize condition grade to standard format."""
    grade = grade.strip().upper()

    mappings = {
        "FINE": "Fine",
        "VG+": "VG+", "VERY GOOD+": "VG+",
        "VG": "VG", "VERY GOOD": "VG",
        "VG-": "VG-", "VERY GOOD-": "VG-",
        "GOOD+": "Good+",
        "GOOD": "Good",
        "FAIR": "Fair",
        "POOR": "Poor",
    }

    return mappings.get(grade, grade)
```

### Score Recalculation

After field extraction, recalculate scores with new data:

```python
# In worker.py after extract_book_fields()
scores = calculate_all_scores(
    purchase_price=book.purchase_price,
    value_mid=book.value_mid,
    publisher_tier=book.publisher.tier if book.publisher else None,
    binder_tier=book.binder.tier if book.binder else None,
    year_start=book.year_start,
    is_complete=book.is_complete,
    condition_grade=book.condition_grade,
    # ... other params
)

book.investment_grade = scores["investment_grade"]
book.strategic_fit = scores["strategic_fit"]
book.collection_impact = scores["collection_impact"]
book.overall_score = scores["overall_score"]
```

### Files Modified

- `backend/app/worker.py` - Field extraction + score recalculation

---

## Phase 6: Bulk Re-analysis

**Approach:** Generate script via prompt when ready (not baked into app)

**Process:**

1. Get list of all book IDs: `bmx-api GET /books?limit=100`
2. For each book, trigger async analysis: `POST /books/{id}/analysis/generate-async`
3. Monitor job completion via status endpoint
4. Verify quality on sample before full batch

**Script Pattern:**

```bash
# Generated when ready - not a permanent feature
for book_id in $(bmx-api GET /books | jq -r '.[].id'); do
    bmx-api POST /books/$book_id/analysis/generate-async
    sleep 5  # Rate limiting
done
```

---

## Implementation Order & Dependencies

```
Phase 1: Binder Tier Migration
    ↓
Phase 2: Scoring Enhancement (depends on Phase 1)
    ↓
Phase 3: Prompt Enhancement (independent)
    ↓
Phase 4: Parser Enhancement (depends on Phase 3 format)
    ↓
Phase 5: Field Extraction (depends on Phase 4)
    ↓
Phase 6: Bulk Re-analysis (manual, after deployment)
```

## Testing Strategy

| Phase | Test Approach |
|-------|---------------|
| 1 | Run migration in staging, verify binder tier via API |
| 2 | Unit tests for scoring, verify book 501 score improves |
| 3 | Generate analysis for test book, verify format |
| 4 | Parse test analysis, verify FMV extraction |
| 5 | Full flow: generate → parse → extract → verify book fields |
| 6 | Re-analyze 5 books, verify quality, then run full batch |

## Rollout Plan

1. Deploy Phases 1-5 to staging
2. Test with book 501 (same book as 489 exemplar)
3. Verify scores match exemplar (~215 vs 100)
4. Deploy to production
5. Run bulk re-analysis on all 70+ books

---

## Files Summary

| Phase | File | Change |
|-------|------|--------|
| 1 | `backend/alembic/versions/xxx_add_binder_tier.py` | Migration |
| 1 | `backend/app/models/binder.py` | Add tier field |
| 1 | `backend/app/schemas/binder.py` | Add tier to schema |
| 2 | `backend/app/services/scoring.py` | Binder tier, DOUBLE TIER 1 |
| 2 | `backend/app/api/v1/books.py` | Pass binder_tier to scoring |
| 2 | `backend/tests/test_scoring.py` | New tests |
| 3 | `infrastructure/prompts/napoleon-framework/v2.md` | New prompt |
| 3 | `backend/app/services/bedrock.py` | Update PROMPT_KEY |
| 4 | `backend/app/utils/markdown_parser.py` | Multi-format extraction |
| 4 | `backend/tests/test_markdown_parser.py` | Parser tests |
| 5 | `backend/app/worker.py` | Field extraction + scores |

---

## Reference

- **Exemplar Book:** <https://app.bluemoxon.com/books/489>
- **Automated Book:** <https://staging.app.bluemoxon.com/books/501>
- **Manual Workflow:** `/Users/mark/Downloads/example_quality_acquistion_flow.md`
- **Napoleon Framework:** `documentation/book_analysis/README.md` (book-collection repo)
