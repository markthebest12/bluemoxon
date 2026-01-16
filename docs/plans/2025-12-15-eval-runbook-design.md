# Eval Runbook Design

**Issue:** #335
**Date:** 2025-12-15
**Status:** Approved

## Overview

The Eval Runbook is a lightweight evaluation report that provides strategic fit scoring, FMV pricing, and acquisition recommendations. It is distinct from the deeper Napoleon Analysis and auto-generates on eBay import.

## Key Features

1. **Auto-generated on eBay import** - Evaluation ready immediately when considering an acquisition
2. **Strategic fit scoring** - Points-based system from ACQUISITION_EVALUATION_PROTOCOL
3. **FMV pricing** - Market comparables from eBay sold listings + AbeBooks
4. **Recommended asking price** - Calculated price to achieve 80+ acquisition score
5. **Manual price override** - Update price after discounts or negotiation, recalculates scoring
6. **Modal display** - Consistent with Napoleon Analysis UX

## Entry Point

Two side-by-side buttons on the book detail page:

```
┌─────────────────────┐  ┌─────────────────────┐
│  📋 Eval Runbook    │  │  📖 Napoleon Analysis│
│      60 pts ⚠️      │  │      Not Generated   │
└─────────────────────┘  └─────────────────────┘
```

- Eval Runbook shows score + PASS/ACQUIRE badge inline
- Napoleon Analysis shows generation status
- Click either to open respective modal

## Modal Layout

### Summary Header

```
╔═══════════════════════════════════════════════════════════════╗
║  EVAL RUNBOOK                                          [X]   ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║   Strategic Fit Score                                         ║
║   ┌─────────────────────────────────────────────────────────┐ ║
║   │██████████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░│ ║
║   └─────────────────────────────────────────────────────────┘ ║
║                    60 / 100                                   ║
║                                                               ║
║              ┌──────────────────┐                             ║
║              │   ⚠️  PASS       │                             ║
║              └──────────────────┘                             ║
║                                                               ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │  Asking      Est. FMV       Recommend      Delta        │  ║
║  │  $275        $180-$220      $160          -$115         │  ║
║  │  [✏️ Edit]                  (for 80+ score)             │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

**Score visualization:**

- Progress bar fills based on score (0-100)
- Color coding: Red (<60), Yellow (60-79), Green (80+)
- Badge shows PASS (yellow) or ACQUIRE (green)

**Pricing row:**

- **Asking** - Current price (editable)
- **Est. FMV** - Market range from comparables
- **Recommend** - Target price for 80+ score
- **Delta** - Gap between asking and recommended

### Price Edit Modal

When clicking [✏️ Edit] on the asking price:

```
╔═══════════════════════════════════════════════════════════════╗
║  Update Asking Price                                   [X]   ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║   Original Listing Price:  $275                               ║
║                                                               ║
║   New Price: [$260________]                                   ║
║                                                               ║
║   Discount Code (optional): [SAVE20_______]                   ║
║                                                               ║
║   Notes: [Seller accepted offer________________]              ║
║          [_______________________________________]            ║
║                                                               ║
║   ┌─────────────────────────────────────────────────────────┐ ║
║   │  Score Impact Preview                                   │ ║
║   │  Current: 60 pts  →  New: 68 pts (+8)                   │ ║
║   │  Status:  PASS    →  Still PASS (need $160 for ACQUIRE) │ ║
║   └─────────────────────────────────────────────────────────┘ ║
║                                                               ║
║              [Cancel]              [Save & Recalculate]       ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

**Price edit features:**

- Shows original listing price for reference
- New price input field
- Optional discount code field (for tracking)
- Notes field for negotiation context
- Live preview of score impact before saving
- Recalculates all scoring on save

### Accordion Sections

```
║  ▼ Item Identification                                        ║
║  ┌───────────────────────────────────────────────────────────┐║
║  │ Title        │ Poems                                      │║
║  │ Author       │ Henry Wadsworth Longfellow                 │║
║  │ Publisher    │ David Bogue, London                        │║
║  │ Date         │ 1854                                       │║
║  │ Binding      │ Full green morocco, publisher's deluxe     │║
║  │ Provenance   │ Armorial bookplate, penciled "1854 £25"    │║
║  └───────────────────────────────────────────────────────────┘║
║                                                               ║
║  ▶ Condition Assessment                      Grade: GOOD+    ║
║  ─────────────────────────────────────────────────────────── ║
║                                                               ║
║  ▶ Strategic Scoring                         60 pts          ║
║  ─────────────────────────────────────────────────────────── ║
║                                                               ║
║  ▶ FMV Pricing                               $180-$220       ║
║  ─────────────────────────────────────────────────────────── ║
║                                                               ║
║  ▶ Critical Issues & Recommendation          ⚠️ 4 issues     ║
║  ─────────────────────────────────────────────────────────── ║
```

Each accordion header shows a preview value. Sections expand to show full details.

### Strategic Scoring (Expanded)

```
║  ▼ Strategic Scoring                                   60 pts ║
║  ┌───────────────────────────────────────────────────────────┐║
║  │ Criterion              │ Points │ Notes                   │║
║  ├────────────────────────┼────────┼─────────────────────────│║
║  │ Tier 1 Publisher       │   0    │ David Bogue - NOT Tier 1│║
║  │ Victorian Era          │  +30   │ ✓ 1854                  │║
║  │ Complete Set           │  +20   │ ✓ Single volume         │║
║  │ Condition              │  +10   │ Good+ (foxing penalty)  │║
║  │ Premium Binding        │   0    │ No binder signature     │║
║  │ Price vs FMV           │   0    │ Above market            │║
║  ├────────────────────────┼────────┼─────────────────────────│║
║  │ TOTAL                  │  60    │ Below 80pt threshold    │║
║  └───────────────────────────────────────────────────────────┘║
```

- Criteria from ACQUISITION_EVALUATION_PROTOCOL
- Points column color-coded (green for earned, gray for 0)
- Notes explain each score decision

### FMV Pricing (Expanded)

```
║  ▼ FMV Pricing                                     $180-$220  ║
║  ┌───────────────────────────────────────────────────────────┐║
║  │                                                           │║
║  │  eBay Sold (last 90 days)                                 │║
║  │  ┌─────────────────────────────────────────────────────┐  │║
║  │  │ Longfellow Poems 1854 Bogue - Good      │ $165  📅7d │  │║
║  │  │ Longfellow Poems 1854 morocco - Fair    │ $142 📅23d │  │║
║  │  │ Longfellow Poetical Works 1856 gilt     │ $195 📅41d │  │║
║  │  └─────────────────────────────────────────────────────┘  │║
║  │  Avg: $167  │  Range: $142-$195                           │║
║  │                                                           │║
║  │  AbeBooks (current listings)                              │║
║  │  ┌─────────────────────────────────────────────────────┐  │║
║  │  │ Poems 1854 First Ed. - Good+            │ $225      │  │║
║  │  │ Poems 1854 Bogue - Very Good            │ $275      │  │║
║  │  │ Poems 1854 morocco binding - Fair       │ $180      │  │║
║  │  └─────────────────────────────────────────────────────┘  │║
║  │  Avg: $227  │  Range: $180-$275                           │║
║  │                                                           │║
║  │  ───────────────────────────────────────────────────────  │║
║  │  Combined FMV Estimate: $180-$220 (weighted to sold)      │║
║  │                                                           │║
║  └───────────────────────────────────────────────────────────┘║
```

- eBay sold listings with recency indicators (days ago)
- AbeBooks current asking prices
- Averages and ranges for each source
- Combined estimate weighted toward actual sales

### Critical Issues & Recommendation (Expanded)

```
║  ▼ Critical Issues & Recommendation            ⚠️ 4 issues    ║
║  ┌───────────────────────────────────────────────────────────┐║
║  │ • Author Outside Collection Focus - Longfellow is        │║
║  │   American, not British Victorian                        │║
║  │ • Publisher Not Strategic - David Bogue not Tier 1       │║
║  │ • No Premium Binder Attribution                          │║
║  │ • Condition Concerns - Heavy foxing on frontispiece      │║
║  └───────────────────────────────────────────────────────────┘║
```

### Analysis Findings (Fixed at Bottom)

```
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                               ║
║  📝 Analysis Findings                                         ║
║  ┌───────────────────────────────────────────────────────────┐║
║  │ This is a handsome Victorian illustrated book with a     │║
║  │ decorative publisher's binding, but it doesn't align     │║
║  │ with your collection strategy.                           │║
║  │                                                           │║
║  │ The binding shows elaborate gilt work that remains       │║
║  │ bright, suggesting careful storage. However, the         │║
║  │ moderate foxing throughout—particularly heavy on the     │║
║  │ frontispiece portrait—indicates exposure to humidity     │║
║  │ at some point. The spine joints show wear consistent     │║
║  │ with age but the structure remains sound.                │║
║  │                                                           │║
║  │ From a strategic standpoint, David Bogue was a           │║
║  │ respectable publisher of Victorian gift books but        │║
║  │ lacks the literary significance of your Tier 1 targets.  │║
║  │ The binding, while attractive, is publisher's deluxe     │║
║  │ rather than a premium trade binding—no Rivière or        │║
║  │ Zaehnsdorf stamps visible on turn-ins.                   │║
║  │                                                           │║
║  │ At the asking price of $275, this represents a ~25%      │║
║  │ premium over recent comparable sales. To meet the 80pt   │║
║  │ acquisition threshold, the price would need to drop to   │║
║  │ approximately $160, offering enough upside to offset     │║
║  │ the non-strategic nature of the acquisition.             │║
║  └───────────────────────────────────────────────────────────┘║
```

- Always visible (not an accordion)
- Full LLM narrative explaining reasoning
- Covers condition observations, strategic fit rationale, pricing logic
- Scrollable if lengthy

## Data Model

### EvalRunbook Table

```sql
CREATE TABLE eval_runbooks (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,

    -- Scoring
    total_score INTEGER NOT NULL,
    score_breakdown JSONB NOT NULL,  -- {criterion: {points, notes}}
    recommendation VARCHAR(20) NOT NULL,  -- 'PASS' or 'ACQUIRE'

    -- Pricing
    original_asking_price DECIMAL(10,2),
    current_asking_price DECIMAL(10,2),
    discount_code VARCHAR(100),
    price_notes TEXT,
    fmv_low DECIMAL(10,2),
    fmv_high DECIMAL(10,2),
    recommended_price DECIMAL(10,2),

    -- FMV Comparables
    ebay_comparables JSONB,  -- [{title, price, days_ago, condition}]
    abebooks_comparables JSONB,  -- [{title, price, condition}]

    -- Content
    condition_grade VARCHAR(20),
    condition_positives TEXT[],
    condition_negatives TEXT[],
    critical_issues TEXT[],
    analysis_narrative TEXT,

    -- Metadata
    generated_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(book_id)
);
```

### Price History (for tracking changes)

```sql
CREATE TABLE eval_price_history (
    id SERIAL PRIMARY KEY,
    eval_runbook_id INTEGER REFERENCES eval_runbooks(id) ON DELETE CASCADE,
    previous_price DECIMAL(10,2),
    new_price DECIMAL(10,2),
    discount_code VARCHAR(100),
    notes TEXT,
    score_before INTEGER,
    score_after INTEGER,
    changed_at TIMESTAMP DEFAULT NOW()
);
```

## API Endpoints

### GET /api/v1/books/{id}/eval-runbook

Returns the eval runbook for a book, or 404 if not generated.

### POST /api/v1/books/{id}/eval-runbook/generate

Triggers generation of eval runbook (usually auto-called on eBay import).

### PATCH /api/v1/books/{id}/eval-runbook/price

Updates the asking price and recalculates scoring.

```json
{
  "new_price": 260.00,
  "discount_code": "SAVE20",
  "notes": "Seller accepted offer"
}
```

Response includes updated scoring and recommendation.

## Generation Flow

1. **eBay Import triggers generation**
   - Extract listing price, title, author, publisher, date
   - Fetch images

2. **FMV Lookup**
   - Query eBay sold listings API (last 90 days)
   - Scrape AbeBooks for current listings
   - Calculate combined FMV range

3. **LLM Evaluation**
   - Send images + metadata to Claude
   - Apply ACQUISITION_EVALUATION_PROTOCOL scoring
   - Generate condition assessment
   - Identify critical issues
   - Write analysis narrative

4. **Calculate Recommended Price**
   - Work backward from 80pt threshold
   - Account for non-price factors (author, publisher, condition)
   - Determine price needed for strategic acquisition

5. **Persist & Display**
   - Save to eval_runbooks table
   - Show button with score on book detail page

## Implementation Notes

- Reuse existing Bedrock service for LLM calls
- FMV lookup should be resilient to API failures (graceful degradation)
- Price recalculation should be fast (no LLM call, just math)
- Consider caching FMV data for 24 hours to reduce API calls
