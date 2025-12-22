# Admin Config Dashboard Design

**Date:** 2025-12-21
**Status:** Design complete, ready for implementation

---

## Overview

Expand the existing `/admin/config` page from a simple currency rates editor into a comprehensive admin dashboard with tabbed interface showing system health, versions, scoring configuration, and entity tiers.

## Tab Structure

| Tab | Purpose | Editable? | Access |
|-----|---------|-----------|--------|
| **Settings** | Currency rates (existing) | Yes | Editor, Admin |
| **System Status** | Health, versions, environment | No | Editor, Admin |
| **Scoring Config** | All tiered_scoring.py constants | No | Editor, Admin |
| **Entity Tiers** | Authors/Publishers/Binders by tier | No | Editor, Admin |

## Navigation

**Profile dropdown menu update:**
```
Profile
Config          <- NEW (editors + admins)
Admin Settings  (admins only)
Sign Out
```

**Router change:** `/admin/config` needs `requiresEditor` instead of `requiresAdmin`

## Data Refresh Behavior

- Data loads on page mount and tab switch
- Manual "Refresh" button (no auto-refresh)
- Single API endpoint: `GET /admin/system-info`

## Tab Designs

### Settings Tab (Existing)

Keep current currency rates editor unchanged:
- GBP to USD rate
- EUR to USD rate
- Save button

### System Status Tab

```
[Alert banner if any health check fails]

Version & Deployment
├── App Version:     2025.12.21-7b471a5
├── Git SHA:         7b471a5f...
├── Deploy Time:     2025-12-21T14:30:00Z
├── Environment:     staging
└── Cold Start:      Yes (latencies may be elevated)

Health Checks                              Latency
├── Database         ✓ healthy             45ms
│   └── Book count: 523
├── S3 Images        ✓ healthy             120ms
│   └── Bucket: bluemoxon-images
├── Cognito          ✓ healthy             89ms
│   └── Pool: bluemoxon-users
└── Config           ✓ healthy
    └── Environment: staging, Debug: false

Bedrock Models
├── sonnet:  us.anthropic.claude-sonnet-4-5-20250929-v1:0
└── opus:    us.anthropic.claude-opus-4-5-20251101-v1:0
```

**Error handling:**
- Alert banner at top if any component unhealthy
- Inline status badges (green checkmark / red X) with error on hover
- Cold start indicator when detected

### Scoring Config Tab

Full breakdown of all constants from `tiered_scoring.py`, organized into groups.
Key tunables marked with star (★).

```
Quality Score Points                        ★ = Key Tunable
├── ★ Publisher Tier 1:           25 pts
├── ★ Publisher Tier 2:           10 pts
├── ★ Binder Tier 1:              30 pts
├── ★ Binder Tier 2:              15 pts
├──   Double Tier 1 Bonus:        10 pts
├──   Era Bonus (1800-1901):      15 pts
├──   Condition Fine:             15 pts
├──   Condition Good:             10 pts
├──   Complete Set:               10 pts
├── ★ Author Priority Cap:        15 pts
├──   Duplicate Penalty:         -30 pts
└──   Large Volume (≥5) Penalty: -10 pts

Strategic Fit Points
├── ★ Publisher Match:            40 pts
├── ★ New Author:                 30 pts
├──   Second Work:                15 pts
└──   Completes Set:              25 pts

Price Position Thresholds
├──   Excellent:    < 70% of FMV
├──   Good:         70-85% of FMV
├──   Fair:         85-100% of FMV
└──   Poor:         > 100% of FMV

Combined Score Weights
├── ★ Quality Weight:             60%
└── ★ Strategic Fit Weight:       40%

Floor Thresholds
├── ★ Strategic Fit Floor:        30
└── ★ Quality Floor:              40

Offer Discounts (by combined score)
├──   70-79:  15% below FMV
├──   60-69:  25% below FMV
├──   50-59:  35% below FMV
├──   40-49:  45% below FMV
├──   0-39:   55% below FMV
├── ★ Strategic Floor Discount:   40%
└── ★ Quality Floor Discount:     50%
```

### Entity Tiers Tab

Three tables in responsive grid (3-column on wide screens, stacked on mobile).
Each table groups entities by tier, showing only Tier 1-3 (excludes null/untiered).

```
┌─────────────────────┬─────────────────────┬─────────────────────┐
│      AUTHORS        │     PUBLISHERS      │      BINDERS        │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ TIER 1              │ TIER 1              │ TIER 1              │
│ • Charles Darwin    │ • Richard Bentley   │ • Zaehnsdorf        │
│ • Charles Lyell     │ • John Murray       │ • Rivière & Son     │
│                     │                     │ • Sangorski & S.    │
│ TIER 2              │ TIER 2              │ • Bayntun           │
│ • Charles Dickens   │ • Chatto & Windus   │                     │
│ • W. Wilkie Collins │ • George Allen      │ TIER 2              │
│                     │                     │ • Morrell           │
│ TIER 3              │ TIER 3              │ • Root & Son        │
│ • John Ruskin       │ • ...               │                     │
│                     │                     │ TIER 3              │
│ (5 total)           │ (8 total)           │ • ...               │
│                     │                     │ (12 total)          │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

## API Design

### New Endpoint: `GET /admin/system-info`

Returns all data for read-only tabs in one response.

```json
{
  "is_cold_start": false,
  "timestamp": "2025-12-21T14:30:00Z",

  "system": {
    "version": "2025.12.21-7b471a5",
    "git_sha": "7b471a5f...",
    "deploy_time": "2025-12-21T14:30:00Z",
    "environment": "staging"
  },

  "health": {
    "overall": "healthy",
    "total_latency_ms": 254,
    "checks": {
      "database": { "status": "healthy", "latency_ms": 45, "book_count": 523 },
      "s3": { "status": "healthy", "latency_ms": 120, "bucket": "bluemoxon-images" },
      "cognito": { "status": "healthy", "latency_ms": 89, "user_pool": "bluemoxon-users" }
    }
  },

  "models": {
    "sonnet": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "opus": "us.anthropic.claude-opus-4-5-20251101-v1:0"
  },

  "scoring_config": {
    "quality_points": {
      "publisher_tier_1": 25,
      "publisher_tier_2": 10,
      "binder_tier_1": 30,
      "binder_tier_2": 15,
      "double_tier_1_bonus": 10,
      "era_bonus": 15,
      "condition_fine": 15,
      "condition_good": 10,
      "complete_set": 10,
      "author_priority_cap": 15,
      "duplicate_penalty": -30,
      "large_volume_penalty": -10
    },
    "strategic_points": {
      "publisher_match": 40,
      "new_author": 30,
      "second_work": 15,
      "completes_set": 25
    },
    "thresholds": {
      "price_excellent": 0.70,
      "price_good": 0.85,
      "price_fair": 1.00,
      "strategic_floor": 30,
      "quality_floor": 40
    },
    "weights": {
      "quality": 0.60,
      "strategic_fit": 0.40
    },
    "offer_discounts": {
      "70-79": 0.15,
      "60-69": 0.25,
      "50-59": 0.35,
      "40-49": 0.45,
      "0-39": 0.55,
      "strategic_floor": 0.40,
      "quality_floor": 0.50
    }
  },

  "entity_tiers": {
    "authors": [
      { "name": "Charles Darwin", "tier": "TIER_1" },
      { "name": "Charles Lyell", "tier": "TIER_1" },
      { "name": "Charles Dickens", "tier": "TIER_2" }
    ],
    "publishers": [
      { "name": "Richard Bentley", "tier": "TIER_1" }
    ],
    "binders": [
      { "name": "Zaehnsdorf", "tier": "TIER_1" }
    ]
  }
}
```

### Existing Endpoint: `GET/PUT /admin/config`

Unchanged - continues to handle currency rates for Settings tab.

## Implementation Notes

### Backend

1. **Cold start detection:** Module-level flag `_is_cold_start = True`, set to `False` after first request
2. **Reuse existing health check functions** from `health.py`: `check_database()`, `check_s3()`, `check_cognito()`
3. **Import scoring constants** from `tiered_scoring.py` module
4. **Entity tier queries:** Simple DB queries with `WHERE tier IN ('TIER_1', 'TIER_2', 'TIER_3')`

### Frontend

1. **Tabbed interface:** Use existing Vue patterns (likely headless UI or custom tabs)
2. **Responsive grid:** Tailwind CSS grid for entity tiers (3-col → stacked)
3. **Status badges:** Green checkmark / red X icons with hover tooltips
4. **Alert banner:** Conditional render at page top when health issues detected

### Router

1. **Add `requiresEditor` meta flag** to router guard
2. **Update `/admin/config` route** from `requiresAdmin: true` to `requiresEditor: true`

### NavBar

1. **Add "Config" menu item** between Profile and Admin Settings
2. **Use `v-if="authStore.isEditor"`** (already exists in auth store)
3. **Link to `/admin/config`**

## Files to Modify

**Backend:**
- `backend/app/api/v1/admin.py` - Add `/system-info` endpoint
- `backend/app/services/tiered_scoring.py` - Export constants dict (or read directly)

**Frontend:**
- `frontend/src/views/AdminConfigView.vue` - Expand to tabbed interface
- `frontend/src/components/layout/NavBar.vue` - Add Config menu item
- `frontend/src/router/index.ts` - Add `requiresEditor` guard logic

## Out of Scope

- Lambda metrics (ephemeral, not useful for manual-refresh dashboard)
- Auto-refresh (manual refresh only)
- Editing scoring config (read-only for now)
- Editing entity tiers (read-only for now)

---

*Design validated via brainstorming skill on 2025-12-21*
