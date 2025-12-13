# Analysis Enrichment Implementation Prompt

**Use this prompt to continue implementation after context compacts.**

---

## Context

You are implementing the Analysis & Acquisition Enrichment feature for BlueMoxon, a Victorian book collection management app. The design is complete and approved.

## Design Document

**Read first:** `docs/plans/2025-12-13-analysis-enrichment-design.md`

## Problem Being Solved

The automated acquisition flow produces lower quality analyses than the manual workflow:
- Book 489 (exemplar, manual): overall_score ~215, all fields populated
- Book 501 (automated): overall_score 100, missing FMV, condition, provenance, notes

Same book (J.R. Green, Zaehnsdorf binding) - gap is entirely due to:
1. Parser can't extract FMV from current format
2. Scoring missing binder tier (+40) and DOUBLE TIER 1 bonus (+15)
3. No field extraction from analysis to book record

## Working Directory

```
/Users/mark/projects/bluemoxon/.worktrees/analysis-enrichment
```

Branch: `feature/analysis-enrichment` (based on `staging`)

## Implementation Phases

### Phase 1: Binder Tier Migration
- Add `tier` column to `binders` table
- Populate Tier 1: Zaehnsdorf, Rivière, Sangorski & Sutcliffe, Bayntun, Hayday
- Populate Tier 2: Bumpus, Sotheran, Root & Son, Morrell

**Files:**
- `backend/alembic/versions/xxx_add_binder_tier.py` (create)
- `backend/app/models/binder.py` (add tier field)
- `backend/app/schemas/binder.py` (add tier to schema)

### Phase 2: Scoring Enhancement
- Add `binder_tier` parameter to `calculate_strategic_fit()`
- Add DOUBLE TIER 1 bonus (+15 when both publisher AND binder are TIER_1)
- Add graduated volume penalty (-10 for 4 vols, -20 for 5+ vols)
- Update scoring breakdown functions

**Files:**
- `backend/app/services/scoring.py`
- `backend/app/api/v1/books.py` (pass binder_tier to scoring)
- `backend/tests/test_scoring.py` (add new tests)

### Phase 3: Prompt Enhancement
- Create `napoleon-framework/v2.md` with:
  - Image analysis instructions (look for binder stamps, provenance markers)
  - Required parseable format for FMV table, condition grade, provenance
  - Conditional sections (DOUBLE TIER 1, Institution)
- Update bedrock.py PROMPT_KEY to v2

**Files:**
- `infrastructure/prompts/napoleon-framework/v2.md` (create)
- `backend/app/services/bedrock.py` (update PROMPT_KEY)

### Phase 4: Parser Enhancement
- Add multi-format FMV extraction (table + range formats)
- Add condition grade extraction with multiple patterns
- Add provenance and notes extraction

**Files:**
- `backend/app/utils/markdown_parser.py`
- `backend/tests/test_markdown_parser.py`

### Phase 5: Field Extraction
- After parsing, populate book fields: value_low/mid/high, condition_grade, provenance, notes
- Recalculate scores with new data

**Files:**
- `backend/app/worker.py`

### Phase 6: Bulk Re-analysis
- Script/prompt to re-analyze all 70+ books (not baked into app)
- Run after Phases 1-5 deployed to production

## Key Files Reference

| File | Purpose |
|------|---------|
| `backend/app/services/scoring.py` | Scoring calculations |
| `backend/app/utils/markdown_parser.py` | Analysis parsing |
| `backend/app/worker.py` | Async analysis worker |
| `backend/app/services/bedrock.py` | Bedrock integration |
| `infrastructure/prompts/napoleon-framework/v1.md` | Current prompt |

## Test Commands

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/analysis-enrichment/backend

# Run scoring tests
poetry run pytest tests/test_scoring.py -v

# Run parser tests
poetry run pytest tests/test_markdown_parser.py -v

# Run all tests
poetry run pytest tests/ -v --tb=short

# Lint
poetry run ruff check .
poetry run ruff format --check .
```

## Verification

After implementation, test with book 501 in staging:
```bash
# Trigger new analysis
bmx-api POST /books/501/analysis/generate-async

# Check status
bmx-api GET /books/501/analysis/status

# Verify scores improved
bmx-api GET /books/501
# Expected: overall_score ~215 (vs current 100)
```

## Reference URLs

- **Exemplar book 489:** https://app.bluemoxon.com/books/489
- **Test book 501:** https://staging.app.bluemoxon.com/books/501
- **Original gaps analysis:** `docs/plans/2025-12-13-scoring-analysis-gaps-reference.md`

## Scoring Formula (After Implementation)

Book 501 should score:
| Component | Points |
|-----------|--------|
| Publisher TIER_1 | +35 |
| Binder TIER_1 | +40 |
| DOUBLE TIER 1 | +15 |
| Victorian Era | +20 |
| Complete Set | +15 |
| Condition (VG) | +15 |
| 4 Volumes | -10 |
| New Author | +30 |
| **Strategic Fit** | **160** |
| Investment Grade (~33% discount) | ~35 |
| Collection Impact | ~30 |
| **Overall Score** | **~225** |

## Start Command

```
Implement Phase 1 (Binder Tier Migration) from the design doc at docs/plans/2025-12-13-analysis-enrichment-design.md. Work in the worktree at /Users/mark/projects/bluemoxon/.worktrees/analysis-enrichment
```
