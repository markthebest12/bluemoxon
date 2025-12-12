# Phase 8: Paste-to-Extract Order Details

## Overview

Add a "Paste Order Details" feature to quickly extract purchase details from eBay order confirmation emails, reducing manual data entry in the acquisition flow.

## User Flow

1. User clicks "Acquire" on a book in Evaluating column
2. AcquireModal opens with empty form
3. User clicks "Paste Order" button (top-right of form)
4. PasteOrderModal opens with textarea
5. User pastes eBay order confirmation email text
6. Clicks "Extract" → calls `POST /api/v1/orders/extract`
7. Backend extracts fields with regex, falls back to Bedrock if confidence < 0.8
8. Modal shows extracted values with confidence indicators
9. User clicks "Apply" → closes PasteOrderModal, populates AcquireModal
10. User reviews, optionally edits, clicks "Confirm Acquire"

## Technical Design

### Backend

#### New Endpoint: `POST /api/v1/orders/extract`

```python
# Request
{
  "text": "Your order has been confirmed\nOrder number: 21-13904-88107\n..."
}

# Response
{
  "order_number": "21-13904-88107",
  "item_price": 239.00,
  "shipping": 17.99,
  "total": 256.99,
  "currency": "GBP",
  "total_usd": 328.95,
  "purchase_date": "2025-01-15",
  "platform": "eBay",
  "estimated_delivery": "2025-01-25",
  "tracking_number": "9400111899223847560123",  # display only, not persisted
  "confidence": 0.92,
  "used_llm": false,
  "field_confidence": {
    "order_number": 0.99,
    "total": 0.95,
    "purchase_date": 0.85,
    "platform": 0.90
  }
}
```

#### Extraction Pipeline

1. `regex_extractor.py` - Pattern matching for eBay formats
2. Calculate confidence per field (0.0-1.0)
3. If overall confidence < 0.8 → call Bedrock LLM
4. Apply currency conversion using rate from admin config
5. Return structured response

#### Regex Patterns

| Field | Pattern Examples | Regex |
|-------|-----------------|-------|
| Order Number | `21-13904-88107` | `\d{2}-\d{5}-\d{5}` |
| Price | `£256.99`, `$123.45` | `[£$€]\s*[\d,]+\.?\d*` |
| Total | "Order total: £256.99" | `total[:\s]+[£$€][\d,.]+` |
| Date | "Jan 15, 2025", "2025-01-15" | Multiple formats |
| Tracking | 20-30 digit numbers | `\b\d{20,30}\b` |
| Delivery | "Estimated delivery: Jan 20-25" | `delivery[:\s]+.+` |

#### Confidence Scoring

- Clear pattern match with label → 0.95+
- Number found without context → 0.7
- Ambiguous/multiple matches → 0.5 → triggers LLM
- Overall threshold for LLM fallback: 0.8

### Admin Config

#### New Endpoint: `GET/PUT /api/v1/admin/config`

```python
# GET response
{
  "gbp_to_usd_rate": 1.28,
  "eur_to_usd_rate": 1.10
}

# PUT request (partial update)
{
  "gbp_to_usd_rate": 1.30
}
```

#### Database Table

```sql
CREATE TABLE admin_config (
  key VARCHAR(50) PRIMARY KEY,
  value JSONB NOT NULL,
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Frontend

#### PasteOrderModal.vue

Two states:

**Input state:**
- Large textarea for pasting order text
- Cancel and Extract buttons

**Results state:**
- List of extracted fields with confidence indicators (✓ or ⚠️)
- Tracking number shown with copy button (not applied to form)
- Back and "Apply to Form" buttons

#### AcquireModal.vue Changes

- Add "Paste Order" button in header area
- Accept extracted values via callback
- Populate form fields when received

#### AdminConfigView.vue

- New route: `/admin/config`
- Simple form with currency rate inputs
- Admin-only access
- Save button with success feedback

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Empty paste | "Please paste order text" (frontend validation) |
| No fields extracted | "Could not extract order details. Try a different format." |
| LLM timeout/failure | Return regex results with lower confidence, warn user |
| Invalid currency | Default to USD, flag for review |
| Admin config missing | Use hardcoded fallback (1.28 for GBP) |

## New Files

### Backend
- `app/api/v1/orders.py` - Extract endpoint
- `app/api/v1/admin.py` - Config endpoints
- `app/services/order_extractor.py` - Regex + LLM logic
- `app/models/admin_config.py` - Config model
- `tests/test_order_extractor.py` - Unit tests

### Frontend
- `src/components/PasteOrderModal.vue`
- `src/views/AdminConfigView.vue`

## Out of Scope

- Shipping update extraction (future enhancement)
- Tracking number persistence (display only)
- PayPal receipt extraction (future)
- Live exchange rate API (use fixed config rate)

## Related Issues

- #198 - Phase 8: Paste-to-extract order details UI
- #196 - Phase 4: Source URL & eBay Integration (completed)
