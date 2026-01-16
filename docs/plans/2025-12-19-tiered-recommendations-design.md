# Tiered Recommendations with Offer Prices and Reasoning

**Issue:** #388
**Status:** Design Complete
**Date:** 2025-12-19
**Author:** Claude + Mark

## Summary

Transform the eval runbook from binary ACQUIRE/PASS to a tiered recommendation system (STRONG_BUY / BUY / CONDITIONAL / PASS) with suggested offer prices and reasoning. Establishes clear two-stage funnel: Eval Runbook (triage) → Napoleon Analysis (deep dive).

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      EVAL RUNBOOK (Auto)                        │
│  Runs on import, gives initial recommendation                   │
│  Output: STRONG_BUY / BUY / CONDITIONAL / PASS                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   HUMAN REVIEW  │ ← Review images, score, reasoning
                    │   (UI display)  │
                    └─────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
              "Run Analysis"       "Skip/Archive"
              (manual button)      (your choice)
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                   NAPOLEON ANALYSIS (Manual)                    │
│  Deep dive with full 8-section report                           │
│  Can OVERRIDE eval runbook recommendation                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  FINAL DECISION │ ← Human decides acquire/pass
                    └─────────────────┘
```

**Key Principles:**

- Human always in the loop - recommendations are suggestions, not gates
- Napoleon Analysis is manually triggered (button click)
- Napoleon can override eval runbook recommendation
- Archive at any stage purges all data (images, analysis, metadata)

## Scoring Model

### Two-Dimension Approach

Separates intrinsic book value from collection-specific strategy:

1. **Quality Score (0-100)** - Is this a good book?
2. **Strategic Fit Score (0-100)** - Does it fit our collection strategy?

### Quality Score (0-100)

Measures intrinsic book desirability, independent of price:

| Factor | Points | Notes |
|--------|--------|-------|
| Tier 1 Publisher | +25 | Bentley, Macmillan, etc. |
| Tier 2 Publisher | +10 | Notable but not premium |
| Tier 1 Binder | +30 | Rivière, Zaehnsdorf, etc. |
| Tier 2 Binder | +15 | Quality trade binding |
| Double Tier 1 Bonus | +10 | Both publisher AND binder Tier 1 |
| Victorian/Romantic Era | +15 | 1800-1901 |
| Condition Fine/VG+ | +15 | Excellent condition |
| Condition Good | +10 | Acceptable condition |
| Complete Set | +10 | No missing volumes |
| Priority Author (capped) | +0-15 | From author.priority_score |
| **Max Total** | **100** | Clean 0-100 scale |

**Penalties (floor at 0):**

- Duplicate title in collection: -30
- 5+ volumes: -10

### Strategic Fit Score (0-100)

Measures collection-specific alignment:

| Factor | Points | Notes |
|--------|--------|-------|
| Publisher matches author requirement | +40 | Collins→Bentley, Dickens→Chapman |
| New author to collection | +30 | Fills gap |
| Second work by author | +15 | Builds depth |
| Completes incomplete set | +25 | Set completion |
| Advances stated collection goal | +20 | Configurable per goal |

### Combined Score

```
Combined Score = (Quality × 0.6) + (Strategic Fit × 0.4)
```

Quality weighted higher, but strategic fit still matters.

### Price Position Categories

| Category | Definition |
|----------|------------|
| EXCELLENT | Price < 70% of FMV mid |
| GOOD | Price 70-85% of FMV mid |
| FAIR | Price 85-100% of FMV mid |
| POOR | Price > 100% of FMV mid |

## Recommendation Matrix

| Combined Score | Excellent Price | Good Price | Fair Price | Poor Price |
|----------------|-----------------|------------|------------|------------|
| **≥ 80** | STRONG_BUY | STRONG_BUY | BUY | CONDITIONAL |
| **60-79** | STRONG_BUY | BUY | CONDITIONAL | PASS |
| **40-59** | BUY | CONDITIONAL | PASS | PASS |
| **< 40** | CONDITIONAL | PASS | PASS | PASS |

### Floor Rules

Prevent "great deal, wrong book" scenarios:

1. **Strategic Fit Floor:** If Strategic Fit < 30, cap recommendation at CONDITIONAL
2. **Quality Floor:** If Quality < 40, cap recommendation at CONDITIONAL

These floors apply regardless of price position.

**Example - Tauchnitz Collins at 71% below FMV:**

- Quality: 65 (good binding, Victorian era)
- Strategic Fit: 10 (wrong publisher for Collins priority)
- Combined: 43
- Matrix says: BUY
- Floor applied: Strategic Fit 10 < 30 → **CONDITIONAL**

## Suggested Offer Price

For CONDITIONAL recommendations, calculate an offer price that makes the deal worthwhile.

### Target Discount by Combined Score

| Combined Score | Target Discount | Rationale |
|----------------|-----------------|-----------|
| 70-79 | 15% below FMV | Good book, needs slight discount |
| 60-69 | 25% below FMV | Decent book, needs meaningful discount |
| 50-59 | 35% below FMV | Marginal book, needs strong discount |
| 40-49 | 45% below FMV | Weak book, only at steep discount |
| < 40 | 55% below FMV | Poor fit, only if bargain |

### Floor-Triggered CONDITIONAL

When CONDITIONAL is due to a floor (not the matrix), use steeper discounts:

- Strategic Fit floor triggered: 40% below FMV minimum
- Quality floor triggered: 50% below FMV minimum

### Formula

```python
suggested_offer = fmv_mid × (1 - target_discount)
```

If asking price is already below suggested offer, note: "Price already below suggested offer - proceed if appealing despite [issue]."

## Reasoning Text

Templated reasoning for consistency and testability:

```python
REASONING_TEMPLATES = {
    "STRONG_BUY": {
        "default": "Excellent {quality_driver} at {discount}% below FMV. Strong strategic fit for {strategy_reason}.",
        "double_tier1": "Double Tier 1 opportunity ({publisher} + {binder}) at {discount}% below FMV.",
    },
    "BUY": {
        "default": "{quality_driver} at {discount}% below FMV. {fit_reason}.",
        "price_driven": "Good value at {discount}% below FMV despite {weakness}.",
    },
    "CONDITIONAL": {
        "strategic_floor": "Quality binding/condition but wrong publisher for {author} collection priority. Consider at ${offer} or below.",
        "quality_floor": "Strategic fit but {condition_issue}. Only acquire at ${offer} or below.",
        "matrix": "Asking price at FMV. {quality_summary}. Offer ${offer} for acceptable margin.",
    },
    "PASS": {
        "default": "{primary_issue}. {secondary_issue}.",
        "overpriced": "Priced {percent}% above FMV with {weakness}.",
    }
}
```

## Score Update Logic

| Trigger | Behavior |
|---------|----------|
| **Eval Runbook refresh** | Recalculates scoring UNLESS Napoleon Analysis already ran (Napoleon is authoritative) |
| **Napoleon Analysis (re)run** | Always updates scoring (overrides everything) |
| **Price change** | Triggers automatic rescore using whichever analysis is current |

```
Price Change Detected
        │
        ▼
  Napoleon exists?
   ┌────┴────┐
   │         │
  YES        NO
   │         │
   ▼         ▼
Rescore    Rescore
using      using
Napoleon   Eval Runbook
weights    weights
```

## Data Model Changes

### New Fields on EvalRunbook

```python
# Tiered recommendation
recommendation_tier: Mapped[str] = mapped_column(String(20), nullable=True)
# Values: STRONG_BUY, BUY, CONDITIONAL, PASS

# Component scores
quality_score: Mapped[int] = mapped_column(Integer, nullable=True)  # 0-100
strategic_fit_score: Mapped[int] = mapped_column(Integer, nullable=True)  # 0-100
combined_score: Mapped[int] = mapped_column(Integer, nullable=True)  # weighted

# Price position
price_position: Mapped[str] = mapped_column(String(20), nullable=True)
# Values: EXCELLENT, GOOD, FAIR, POOR

# Offer price (for CONDITIONAL)
suggested_offer: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=True)

# Reasoning
recommendation_reasoning: Mapped[str] = mapped_column(String(500), nullable=True)

# Floor flags (for transparency)
strategic_floor_applied: Mapped[bool] = mapped_column(default=False)
quality_floor_applied: Mapped[bool] = mapped_column(default=False)

# Scoring version (for auditing)
scoring_version: Mapped[str] = mapped_column(String(20), default="2025-01")

# Score source tracking
score_source: Mapped[str] = mapped_column(String(20), default="eval_runbook")
# Values: "eval_runbook", "napoleon"

# Price change detection
last_scored_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=True)

# Napoleon Analysis fields
napoleon_recommendation: Mapped[str] = mapped_column(String(20), nullable=True)
napoleon_reasoning: Mapped[str] = mapped_column(Text, nullable=True)
napoleon_analyzed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
```

### Backward Compatibility

Keep existing `recommendation` field:

- Map STRONG_BUY/BUY → "ACQUIRE"
- Map CONDITIONAL/PASS → "PASS"

Frontend reads `recommendation_tier` if present, falls back to `recommendation`.

## Frontend Display

### Recommendation Badge Styling

| Tier | Color | Icon |
|------|-------|------|
| STRONG_BUY | Green (bold) | ✓✓ |
| BUY | Green | ✓ |
| CONDITIONAL | Amber/Yellow | ⚠ |
| PASS | Red/Gray | ✗ |

### Modal Layout

```
┌─────────────────────────────────────────────┐
│ EVAL RUNBOOK: [Book Title]                  │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │ [STRONG_BUY]  Quality: 85/100       │    │
│  │               Strategic Fit: 75/100 │    │
│  │               Price: EXCELLENT      │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  "Tier 1 publisher (Bentley) with Victorian │
│   era at 45% below FMV. Fills Collins gap." │
│                                             │
├─────────────────────────────────────────────┤
│ PRICING                                     │
│  Asking: $150  |  FMV: $250-$300           │
│  [For CONDITIONAL: Suggested Offer: $175]   │
├─────────────────────────────────────────────┤
│ SCORE BREAKDOWN (expandable)                │
│  • Tier 1 Publisher (Bentley): +25          │
│  • Victorian Era (1862): +15                │
│  • Condition VG+: +15                       │
│  • Priority Author (Collins): +15           │
└─────────────────────────────────────────────┘
```

### Override Display

If Napoleon Analysis exists and differs from eval runbook:

- Show both recommendations
- Indicate Napoleon as override with explanation
- Visual indicator (e.g., "Napoleon Analysis updated recommendation")

## Archive Cleanup

When a book is archived at any stage, purge all associated data:

- Book record
- Images (S3 objects + database records)
- Eval Runbook
- Napoleon Analysis
- FMV comparables
- Any other linked metadata

This keeps the system clean and avoids orphaned data/storage costs.

## Migration Strategy

1. Add new columns as nullable
2. Backfill existing runbooks with new scores (async job)
3. Frontend reads `recommendation_tier` if present, falls back to `recommendation`
4. Deprecate old `recommendation` field after transition period

## Implementation Phases

### Phase 1: Scoring Engine

- [ ] Create `calculate_quality_score()` function
- [ ] Create `calculate_strategic_fit_score()` function
- [ ] Create `calculate_combined_score()` function
- [ ] Create `determine_price_position()` function
- [ ] Create `apply_recommendation_matrix()` with floors
- [ ] Unit tests for all scoring functions

### Phase 2: Data Model

- [ ] Add new columns to EvalRunbook model
- [ ] Create Alembic migration
- [ ] Update EvalRunbook schema (Pydantic)
- [ ] Backward compatibility mapping

### Phase 3: Offer Price & Reasoning

- [ ] Create `calculate_suggested_offer()` function
- [ ] Create `generate_reasoning()` with templates
- [ ] Unit tests

### Phase 4: Integration

- [ ] Update `generate_eval_runbook()` to use new scoring
- [ ] Add score update logic (price change detection)
- [ ] Add Napoleon override support
- [ ] Integration tests

### Phase 5: Frontend

- [ ] Update eval runbook modal with new display
- [ ] Add recommendation badges with styling
- [ ] Add suggested offer display for CONDITIONAL
- [ ] Add score breakdown expandable section
- [ ] Add Napoleon override indicator

### Phase 6: Archive Cleanup

- [ ] Implement cascade delete for book archive
- [ ] S3 image cleanup on archive
- [ ] Test data purge completeness

## Success Criteria

- [ ] Recommendations use tiered system (STRONG_BUY/BUY/CONDITIONAL/PASS)
- [ ] CONDITIONAL recommendations include suggested offer price
- [ ] All recommendations include reasoning text
- [ ] Strategic fit floor prevents "wrong book, great deal" BUY recommendations
- [ ] Napoleon Analysis can override eval runbook recommendation
- [ ] Price changes trigger rescore
- [ ] Archive purges all associated data
- [ ] Backward compatible with existing `recommendation` field
