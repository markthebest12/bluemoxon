# Tiered Recommendations Design - Eval Runbook Parity with Prompting Approach

**Date:** 2025-12-16
**Status:** DRAFT
**Depends on:** #384 (FMV Accuracy Design)

---

## Problem

The eval runbook produces binary recommendations (ACQUIRE/PASS at 80-point threshold) without:
- Nuanced recommendation tiers (STRONG BUY vs CONDITIONAL)
- Suggested offer prices for borderline items
- Reasoning explaining the recommendation

The prompting-based evaluation approach (Claude Code) produces richer output like:
> "CONDITIONAL BUY at £700-750 - asking price is at FMV, not discounted"

**Goal:** Bring BMX eval runbook output to parity with the prompting approach.

---

## Solution Overview

Combine quality score with FMV position to determine recommendation tier, calculate offer prices for CONDITIONAL items, and generate reasoning statements.

### Data Flow

```
Quality Score (0-120) + FMV Data (low/high/confidence)
    |
    v
Hybrid Matrix (score × FMV position → tier)
    |
    v
Offer Calculation (if CONDITIONAL)
    |
    v
Reasoning Generation (Claude-powered)
    |
    v
Enhanced Response: tier, offer, reasoning
```

---

## Section 1: Recommendation Tier Logic

**Hybrid Matrix: Score × FMV Position → Recommendation**

| | Price < 80% FMV | Price 80-100% FMV | Price > 100% FMV |
|---|---|---|---|
| **Score ≥ 90** | STRONG BUY | BUY | CONDITIONAL |
| **Score 70-89** | BUY | CONDITIONAL | PASS |
| **Score < 70** | CONDITIONAL | PASS | PASS |

**Tier definitions:**
- **STRONG BUY** - Act immediately, excellent value
- **BUY** - Solid acquisition at fair price
- **CONDITIONAL** - Worth acquiring only at reduced price (offer required)
- **PASS** - Does not meet collection criteria or significantly overpriced

**FMV position calculation:**
```python
fmv_midpoint = (fmv_low + fmv_high) / 2
if asking_price < fmv_midpoint * 0.8:
    position = "below"
elif asking_price <= fmv_midpoint:
    position = "at"
else:
    position = "above"
```

---

## Section 2: Offer Price Calculation

**When recommendation is CONDITIONAL, calculate suggested offer:**

```python
target_offer = fmv_low + (fmv_high - fmv_low) * score_factor

# score_factor based on quality score:
if score >= 90:
    score_factor = 0.75  # Aim for 75th percentile of FMV range
elif score >= 70:
    score_factor = 0.50  # Aim for midpoint
else:
    score_factor = 0.25  # Aim for 25th percentile
```

**Example (Lockhart/Leighton set):**
- FMV range: £900-£1,200
- Score: 85 → score_factor = 0.50
- Target offer: £900 + (£300 × 0.50) = **£1,050**
- Asking: £950 → Already below target, upgrade to **BUY**

**Safeguards:**
- Never suggest offer below `fmv_low`
- Never suggest offer above asking price
- If `fmv_confidence` is "low" or FMV data missing, skip offer and note "Insufficient market data for offer recommendation"

---

## Section 3: Reasoning Output

**Generate a 1-2 sentence reasoning statement explaining the recommendation.**

Template structure:
```
[Price position statement]. [Key value factors]. [Action guidance if CONDITIONAL].
```

**Examples by tier:**

| Tier | Example Reasoning |
|------|-------------------|
| STRONG BUY | "Priced 30% below FMV for comparable 7-volume sets. First edition with authenticated Leighton binding represents strong value." |
| BUY | "Fair market price for a complete Victorian set in very good condition. Premium binding justifies acquisition." |
| CONDITIONAL | "Asking price at FMV ceiling. Recommend offer at £700-750 to achieve appropriate discount for collection standards." |
| PASS | "Single volume priced at complete set levels. Condition issues (foxing, loose hinges) not reflected in price." |

**Implementation:** Claude generates this during eval runbook creation, using the calculated FMV data and score breakdown as context. Add to the existing Bedrock prompt.

---

## Section 4: Schema Changes

**New fields in eval runbook response:**

```python
class EvalRunbookResponse(BaseModel):
    # Existing fields (unchanged)
    score: int                           # 0-120
    recommendation: str                  # "ACQUIRE" or "PASS" (kept for backward compat)

    # New fields
    recommendation_tier: str             # "STRONG_BUY" | "BUY" | "CONDITIONAL" | "PASS"
    suggested_offer: float | None        # Only populated for CONDITIONAL
    suggested_offer_currency: str        # "USD" | "GBP"
    reasoning: str                       # 1-2 sentence explanation
    fmv_position: str                    # "below" | "at" | "above"
```

**Backward compatibility:**
- Keep existing `recommendation` field (map STRONG_BUY/BUY → "ACQUIRE", CONDITIONAL/PASS → "PASS")
- New fields are additive, no breaking changes
- Frontend can adopt new fields incrementally

---

## Section 5: Dependencies & Sequencing

**This enhancement depends on #384 (FMV Accuracy Design):**

The tiered recommendation system requires reliable FMV data with confidence levels. Without #384:
- FMV range may be based on irrelevant comparables (single volumes vs sets)
- No `fmv_confidence` field to know when to skip offer calculation
- Price position calculation would be unreliable

**Recommended sequence:**
1. **#384** - Implement context-aware FMV lookup (prerequisite)
2. **This issue** - Add tiered recommendations, offer prices, reasoning

Can be developed in parallel if #384 is in progress - this issue's logic just needs the FMV response shape defined.

---

## Files to Modify

| File | Changes |
|------|---------|
| `backend/app/services/eval_generation.py` | Add `_calculate_recommendation_tier()`, `_calculate_offer_price()`, update `generate_eval_runbook()` |
| `backend/app/schemas/eval_runbook.py` | Add new response fields |
| `backend/app/services/bedrock.py` | Update prompt to generate reasoning |
| `frontend/src/components/EvalRunbookModal.tsx` | Display tier, offer, reasoning |

---

## Acceptance Criteria

- [ ] Recommendation tier calculated from score × FMV position matrix
- [ ] CONDITIONAL recommendations include suggested offer price
- [ ] All recommendations include 1-2 sentence reasoning
- [ ] Response includes `fmv_position` field
- [ ] Backward compatible with existing `recommendation` field
- [ ] Frontend displays new fields in eval runbook modal
