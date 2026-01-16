# Order Tracking Design

**Date:** 2025-12-13
**Issue:** #238
**Status:** Approved

## Overview

Add ability to track shipments for IN_TRANSIT books. Tracking is fully optional - users can mark items received without adding tracking info.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Tracking required? | No, fully optional | Some sellers (UK dealers, estate sales) don't provide tracking |
| Carrier API integration? | No, just generate URLs | Complexity not worth it - user clicks link to see full details |
| UI placement | Dedicated "Add Tracking" button | Consistent with existing "Mark Received" button pattern |
| Carrier selection | Auto-detect from number | Smoother UX; user can override if needed |
| Display after adding | Carrier + truncated number as link | Informative at a glance without clutter |

## Data Model

**New fields on Book model:**

```python
tracking_number: Mapped[str | None] = mapped_column(String(100))
tracking_carrier: Mapped[str | None] = mapped_column(String(50))
tracking_url: Mapped[str | None] = mapped_column(String(500))
```

**Supported carriers with URL templates:**

| Carrier | URL Template |
|---------|-------------|
| USPS | `https://tools.usps.com/go/TrackConfirmAction?tLabels={number}` |
| UPS | `https://www.ups.com/track?tracknum={number}` |
| FedEx | `https://www.fedex.com/fedextrack/?trknbr={number}` |
| DHL | `https://www.dhl.com/en/express/tracking.html?AWB={number}` |
| Royal Mail | `https://www.royalmail.com/track-your-item#/tracking-results/{number}` |
| Parcelforce | `https://www.parcelforce.com/track-trace?trackNumber={number}` |
| Other | User provides full URL manually |

**Auto-detection patterns:**

| Carrier | Pattern |
|---------|---------|
| USPS | 20-22 digits, or starts with 94/93/92 |
| UPS | Starts with "1Z" + 16 alphanumeric |
| FedEx | 12, 15, or 20 digits |
| DHL | 10 digits |
| Royal Mail | 2 letters + 9 digits + 2 letters (e.g., AB123456789GB) |

If no pattern matches, prompt user to select carrier manually.

## API

**Endpoint:**

```text
PATCH /api/v1/books/{book_id}/tracking
```

**Request:**

```json
{
  "tracking_number": "1Z999AA10123456784",
  "tracking_carrier": "UPS",
  "tracking_url": null
}
```

- `tracking_number`: Required unless `tracking_url` provided
- `tracking_carrier`: Optional if auto-detectable from number
- `tracking_url`: Optional manual override (skips URL generation)

**Response:** Standard `BookResponse` with tracking fields populated.

**Validation:**

- Book must be in `IN_TRANSIT` status (400 otherwise)
- If carrier cannot be auto-detected and not provided, return 400

**Authorization:** Requires editor role.

## Frontend Components

### AddTrackingModal.vue

```text
┌─────────────────────────────────────┐
│  Add Tracking                    ✕  │
├─────────────────────────────────────┤
│                                     │
│  Tracking Number                    │
│  ┌─────────────────────────────────┐│
│  │ 1Z999AA10123456784              ││
│  └─────────────────────────────────┘│
│                                     │
│  Carrier: UPS (auto-detected)       │
│  ┌─────────────────────────────────┐│
│  │ UPS                          ▼ ││
│  └─────────────────────────────────┘│
│                                     │
│  [If "Other" selected:]             │
│  Tracking URL                       │
│  ┌─────────────────────────────────┐│
│  │ https://...                     ││
│  └─────────────────────────────────┘│
│                                     │
│         [Cancel]  [Save Tracking]   │
└─────────────────────────────────────┘
```

**Behavior:**

- On number input blur → run auto-detect, show hint
- Carrier dropdown always visible for override
- "Other" shows URL input field
- Save disabled until valid input

### IN_TRANSIT Card Changes

**Before tracking:**

```text
[Add Tracking]  [Mark Received]
```

**After tracking:**

```text
UPS: 1Z99...6784 →  [Mark Received]
```

- Truncate: first 4 + "..." + last 4 characters
- Entire text is clickable link (opens new tab)
- Arrow (→) indicates external link

## Implementation Plan

### Phase 1: Backend

1. Create migration: `add_tracking_fields.py`
2. Update `Book` model with new fields
3. Update `BookResponse` schema
4. Add `PATCH /books/{id}/tracking` endpoint
5. Implement carrier auto-detection utility
6. Unit tests for detection patterns

### Phase 2: Frontend

1. Create `AddTrackingModal.vue`
2. Add `addTracking()` to acquisitions store
3. Update `AcquisitionsView.vue` IN_TRANSIT cards
4. Component tests

## Testing Checklist

- [ ] Add tracking with auto-detected carrier (UPS, USPS, FedEx)
- [ ] Add tracking with manual carrier override
- [ ] Add tracking with "Other" carrier + manual URL
- [ ] Verify tracking link opens correct carrier page
- [ ] Verify "Mark Received" works with/without tracking
- [ ] Verify tracking persists after refresh
- [ ] Verify only IN_TRANSIT books can add tracking

## Out of Scope

- Extract `order_number` to dedicated field (currently in notes)
- Tracking notifications/reminders
- Bulk tracking import
- Carrier API integration for delivery estimates
