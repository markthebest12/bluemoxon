# Acquisitions Button Visual Cleanup Design

**Issue:** #461
**Date:** 2025-12-19

## Problem

The Analysis and Eval Runbook buttons on Acquisitions view cards have two issues:

1. Buttons are centered and spread out - looks awkward
2. Eval Runbook section is missing Generate/Regenerate buttons

## Solution

### Layout: Stacked Compact (Left-Aligned)

Change from centered/spread to left-aligned compact rows:

```
┌───────────────────────────────────────┐
│ 📄 View Analysis 🔄                   │
│ 📋 Eval Runbook  🔄                   │
└───────────────────────────────────────┘
```

**CSS Changes:**

- Remove `flex-1` from buttons (stops stretching)
- Remove `justify-center` from buttons (left-aligns text)
- Add `justify-start` to container rows
- Keep `gap-1` between icon and text, `gap-3` between buttons

### Eval Runbook Buttons

Add Generate/Regenerate buttons mirroring the Analysis pattern:

| State | What Shows |
|-------|-----------|
| Has runbook, not running | 📋 Eval Runbook + 🔄 (admin) |
| Has runbook, job running | ⏳ Queued.../Generating... |
| No runbook, not running | ⚡ Generate Runbook (admin) |
| No runbook, job running | ⏳ Queued.../Generating... |

**Permissions:** Generate/Regenerate visible to `authStore.isAdmin` only.

**Handler:** Reuse existing `handleGenerateEvalRunbook(bookId)` function.

Note: Generate button is a rare fallback - eval runbooks are normally auto-generated on eval save.

### Scope

Apply changes to all 3 columns in Acquisitions view:

- Evaluating (yellow)
- In Transit (blue)
- Received (green)

### Files to Modify

- `frontend/src/views/AcquisitionsView.vue` - 3 column templates

### Out of Scope

- No backend changes needed
- No new store functions needed
- BookDetailView has its own buttons (issue #459)
