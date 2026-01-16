# Acquisitions Dashboard Design

**Date:** 2025-12-10
**Status:** Approved
**Author:** Mark + Claude

## Overview

Replace the manual, file-based acquisition workflow with an in-app acquisitions dashboard. Books flow through EVALUATING → IN_TRANSIT → ON_HAND stages with automated scoring and Bedrock-powered analysis generation.

## Goals

- **Reduce manual coordination** - No more updating 6+ files/systems per acquisition
- **Eliminate data redundancy** - Enter order details once, everything derives from it
- **Automate Napoleon analysis** - Bedrock generates valuations, not manual Claude sessions
- **Two-environment sync eliminated** - Single source of truth in bmx
- **Mobile/web access** - Evaluate and acquire from anywhere, not just workstation

## Data Model Changes

### New Status Flow

```
EVALUATING → IN_TRANSIT → ON_HAND → SOLD/REMOVED
                ↓
            (CANCELED)
```

### New/Modified Fields on `books` Table

| Field | Type | Description |
|-------|------|-------------|
| `status` | enum | Add `EVALUATING`, `CANCELED` to existing values |
| `source_url` | string | eBay/Etsy listing URL (nullable) |
| `source_item_id` | string | Platform item ID extracted from URL (nullable) |
| `estimated_delivery` | date | Expected delivery date (nullable) |
| `scoring_snapshot` | jsonb | Scores captured at acquisition time |

### `scoring_snapshot` Structure

```json
{
  "captured_at": "2025-12-10T...",
  "purchase_price": 164.14,
  "fmv_at_purchase": {"low": 400, "mid": 475, "high": 550},
  "discount_pct": 65,
  "investment_grade": 88.5,
  "strategic_fit": {"score": 7, "max": 7, "criteria": [...]},
  "collection_position": {"items_before": 81, "volumes_before": 264}
}
```

## API Changes

### Acquisition Promotion

```
PATCH /books/{id}/acquire
```

**Request body:**

```json
{
  "purchase_price": 164.14,
  "purchase_date": "2025-12-10",
  "order_number": "19-13940-40744",
  "place_of_purchase": "eBay",
  "estimated_delivery": "2025-12-19"
}
```

**Response:** Book with `status: IN_TRANSIT` and populated `scoring_snapshot`.

### Order Detail Extraction

```
POST /books/parse-order-details
```

**Request body:**

```json
{
  "text": "Order date: Dec 10, 2025\nOrder total: US $164.14\n..."
}
```

**Response:**

```json
{
  "purchase_price": 164.14,
  "purchase_date": "2025-12-10",
  "order_number": "19-13940-40744"
}
```

### Listing Extraction

```
POST /books/parse-listing
```

**Request body:**

```json
{
  "url": "https://www.ebay.com/itm/317643900374"
}
```

**Response:** Extracted listing details with suggested author/publisher/binder matches.

### Analysis Generation

```
POST /books/{id}/generate-analysis
```

**Query param:** `?full=true` for full Napoleon (auto-set if price > $450)

### Existing Endpoints

`PATCH /books/{id}/status` unchanged for ON_HAND, CANCELED transitions.

## UI: Acquisitions Dashboard

**Location:** `/admin/acquisitions` (admin/editor only)

### Layout

Three-column Kanban-style board:

```
┌─────────────────┬─────────────────┬─────────────────┐
│   EVALUATING    │   IN TRANSIT    │    RECEIVED     │
│   (Watchlist)   │   (Acquired)    │   (Last 30d)    │
├─────────────────┼─────────────────┼─────────────────┤
│ ┌─────────────┐ │ ┌─────────────┐ │ ┌─────────────┐ │
│ │ Ruskin      │ │ │ Shelley     │ │ │ Byron       │ │
│ │ $165 ask    │ │ │ $164 paid   │ │ │ $280 paid   │ │
│ │ FMV: $475   │ │ │ 65% disc    │ │ │ Score: 92.1 │ │
│ │ [Acquire]   │ │ │ Due: Dec 19 │ │ │ Score: 88.5 │ │
│ └─────────────┘ │ └─────────────┘ │ └─────────────┘ │
│ ┌─────────────┐ │                 │                 │
│ │ + Add Item  │ │                 │                 │
│ └─────────────┘ │                 │                 │
└─────────────────┴─────────────────┴─────────────────┘
```

### Card Actions

- **EVALUATING:** "Acquire" (opens order details form), "Delete" (reject)
- **IN_TRANSIT:** "Mark Received", "Cancel Order", view scoring
- **RECEIVED:** View full scoring summary, link to book detail

### Top Bar Stats (Admin/Editor Only)

- Monthly spend: $X,XXX / $Y,YYY budget
- Items this month: X acquired
- Avg discount: XX%

### Role Visibility

- **Admin/Editor:** Full dashboard with spending, prices, discounts
- **Viewer:** No access to acquisitions dashboard or spending info

## UI: Add to Watchlist Flow

### Step 1: Paste URL

```
┌────────────────────────────────────────┐
│ Add to Watchlist                       │
├────────────────────────────────────────┤
│ eBay/Etsy URL:                         │
│ ┌────────────────────────────────────┐ │
│ │ https://www.ebay.com/itm/31764...  │ │
│ └────────────────────────────────────┘ │
│                                        │
│              [Fetch Listing]           │
└────────────────────────────────────────┘
```

### Step 2: Review & Enrich

```
┌────────────────────────────────────────┐
│ Confirm Details                        │
├────────────────────────────────────────┤
│ Title: [The Queen of the Air        ]  │
│ Author: [Ruskin_____________] (lookup) │
│ Publisher: [Smith Elder_____] (lookup) │
│ Binder: [Zaehnsdorf________] (lookup)  │
│ Asking Price: [$165________________]   │
│ Date: [1869____]  Volumes: [1___]      │
│                                        │
│ FMV Estimate:                          │
│ Low [$400] Mid [$475] High [$550]      │
│                                        │
│ ☑ Generate analysis (auto for >$450)   │
│                                        │
│         [Cancel]  [Add to Watchlist]   │
└────────────────────────────────────────┘
```

Bedrock extracts listing details and suggests author/publisher/binder matches.

## UI: Acquisition Flow

### Manual Entry

```
┌────────────────────────────────────────┐
│ Acquire: The Queen of the Air          │
├────────────────────────────────────────┤
│ ○ Enter manually  ○ Paste order text   │
├────────────────────────────────────────┤
│ Purchase Price: [$164.14_________]     │
│ Purchase Date:  [2025-12-10______]     │
│ Order Number:   [19-13940-40744__]     │
│ Platform:       [eBay___________] ▼    │
│ Est. Delivery:  [2025-12-19______]     │
│                                        │
│           [Cancel]  [Confirm Acquire]  │
└────────────────────────────────────────┘
```

### Paste Order Text

Radio toggle to paste notification text, click "Extract" to populate fields via Bedrock.

On confirm: Calls `PATCH /books/{id}/acquire`, generates full Napoleon if not already present.

## UI: Scoring Summary View

```
┌─────────────────────────────────────────────────────┐
│ Scoring Summary: The Queen of the Air              │
│ Acquired Dec 10, 2025                              │
├─────────────────────────────────────────────────────┤
│ PURCHASE PERFORMANCE                               │
│ ┌─────────────────────────────────────────────────┐│
│ │ Purchase Price    $164.14                       ││
│ │ FMV at Purchase   $400 - $475 - $550            ││
│ │ Discount          65% ████████████████░░░░      ││
│ │ Savings           $310.86                       ││
│ └─────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────┤
│ INVESTMENT GRADE: 88.5/100                         │
│ ┌─────────────────────────────────────────────────┐│
│ │ Binding Quality (Zaehnsdorf)  25%  92  → 23.00 ││
│ │ Acquisition Value (65% disc)  25%  95  → 23.75 ││
│ │ Strategic Fit                 20%  90  → 18.00 ││
│ │ Condition                     15%  85  → 12.75 ││
│ │ Content/Author Significance   10%  88  →  8.80 ││
│ │ Provenance                     5%  45  →  2.25 ││
│ └─────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────┤
│ STRATEGIC FIT: 7/7 ✓                               │
│ ✓ Target Author    ✓ Tier 1 Bindery                │
│ ✓ Tier 1 Publisher ✓ Victorian Era                 │
│ ✓ Single Volume    ✓ 40%+ Discount                 │
│ ✓ No Duplicates                                    │
├─────────────────────────────────────────────────────┤
│ COLLECTION IMPACT                                  │
│ Items: 81 → 82    Volumes: 264 → 265               │
│ Value: $40,233 → $40,708 (+$475)                   │
└─────────────────────────────────────────────────────┘
```

Admin/editor only - viewers cannot see this view.

## Bedrock Integration

### AWS Setup

- Use existing AWS infrastructure (same account as bmx API)
- Bedrock Claude model: `anthropic.claude-3-sonnet`
- IAM role for Lambda to call Bedrock

### Call Types

| Type | Endpoint | Tokens | Cost |
|------|----------|--------|------|
| Listing extraction | `POST /books/parse-listing` | ~500-1000 | ~$0.005 |
| Light analysis | `POST /books/{id}/generate-analysis` | ~2000 | ~$0.01-0.02 |
| Full Napoleon | `POST /books/{id}/generate-analysis?full=true` | ~8000 | ~$0.08-0.12 |

Full Napoleon auto-triggers for items with asking price > $450.

## Migration & Cleanup

### Database Migration

1. Add `EVALUATING` and `CANCELED` to status enum
2. Add columns: `source_url`, `source_item_id`, `estimated_delivery`, `scoring_snapshot`
3. No data migration needed - existing books stay as-is

### Deprecations

| What | Replaced By |
|------|-------------|
| Local PRE_ analysis files | `status: EVALUATING` in bmx |
| `documentation/book_analysis/` folder | Archive only |
| PENDING_DELIVERIES.txt | IN_TRANSIT status + `estimated_delivery` |
| Victorian guide manual updates | Collection stats from API |
| December targets spending tracking | Dashboard stats |

### What Stays

- `bmx-api` CLI tool (scripting, bulk operations)
- Analysis markdown backup in git (optional export)
- Collecting philosophy docs (strategy, not operational)

### CLAUDE.md Updates

- Remove PRE_ file workflow
- Update acquisition workflow to point to bmx UI
- Keep `bmx-api` CLI docs for power-user use
- Add note: "Acquisitions dashboard at /admin/acquisitions"

## Implementation Order

| Phase | Work | Dependency |
|-------|------|------------|
| 1 | Database: new status values, new columns | None |
| 2 | API: `/acquire` endpoint, scoring calculation | Phase 1 |
| 3 | UI: Acquisitions dashboard (static layout) | Phase 1 |
| 4 | UI: Manual acquire flow (form only) | Phase 2, 3 |
| 5 | Bedrock: Listing extraction | AWS setup |
| 6 | UI: Add-to-watchlist flow | Phase 3, 5 |
| 7 | Bedrock: Analysis generation | Phase 5 |
| 8 | UI: Paste-to-extract order details | Phase 4, 5 |
| 9 | Cleanup: CLAUDE.md, deprecate local files | Phase 4 |

## Open Questions

None - design approved.
