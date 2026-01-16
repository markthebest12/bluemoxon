# Carrier API Support Design

**Issue:** #516
**Date:** 2026-01-02
**Status:** Approved

## Summary

Add API integration for multiple shipping carriers to enable:

- Real-time tracking status display in UI
- Estimated delivery date population
- Proactive notifications (email, SMS, in-app)

## Carriers

| Priority | Carrier | Tracking Pattern | Notes |
|----------|---------|------------------|-------|
| 1 | UPS | `1Z[A-Z0-9]{16}` | Existing - move to plugin |
| 2 | DHL | `\d{10}` | Clean public JSON API |
| 3 | USPS | `(94\|93\|92)\d{18,20}` or `\d{20,22}` | US domestic |
| 4 | FedEx | `\d{12}, \d{15}, \d{20}` | International |
| 5 | Royal Mail | `[A-Z]{2}\d{9}[A-Z]{2}` | UK domestic |
| 6 | Pitney Bowes | `UPAA\d+` | eBay Global Shipping |

## Architecture

```text
backend/app/services/
├── tracking.py              # Existing - detect_carrier(), generate_url()
├── tracking_poller.py       # NEW - hourly job orchestrator
├── notifications.py         # NEW - email/SMS/in-app dispatch
└── carriers/                # NEW - plugin directory
    ├── __init__.py          # Registry + base interface
    ├── base.py              # Abstract CarrierClient class
    ├── ups.py               # Existing logic moved here
    ├── usps.py              # NEW
    ├── fedex.py             # NEW
    ├── dhl.py               # NEW
    ├── royal_mail.py        # NEW
    └── pitney_bowes.py      # NEW
```

## Database Changes

### Acquisitions table (new columns)

```sql
ALTER TABLE acquisitions ADD COLUMN tracking_status VARCHAR(100);
ALTER TABLE acquisitions ADD COLUMN tracking_last_checked TIMESTAMP;
ALTER TABLE acquisitions ADD COLUMN tracking_active BOOLEAN DEFAULT FALSE;
ALTER TABLE acquisitions ADD COLUMN tracking_delivered_at TIMESTAMP;
```

### Users table (new columns)

```sql
ALTER TABLE users ADD COLUMN notify_tracking_email BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN notify_tracking_sms BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN phone_number VARCHAR(20);
```

### Notifications table (new)

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    acquisition_id UUID REFERENCES acquisitions(id) ON DELETE SET NULL,
    message TEXT NOT NULL,
    read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_notifications_user_unread ON notifications(user_id, read) WHERE read = FALSE;
```

## Carrier Plugin Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

@dataclass
class TrackingResult:
    status: str                          # "In Transit", "Delivered", "Exception"
    status_detail: str | None = None
    estimated_delivery: date | None = None
    delivered_at: datetime | None = None
    location: str | None = None
    error: str | None = None

class CarrierClient(ABC):
    name: str

    @abstractmethod
    def fetch_tracking(self, tracking_number: str) -> TrackingResult:
        pass

    @classmethod
    def can_handle(cls, tracking_number: str) -> bool:
        return False
```

## Polling System

- **Trigger:** EventBridge rule, hourly (`rate(1 hour)`)
- **Target:** Existing Lambda with `action=poll_tracking`
- **Lifecycle:** Start when tracking number added, stop 7 days after "Delivered"

```python
def poll_all_active_tracking(db: Session) -> dict:
    active = db.query(Acquisition).filter(
        Acquisition.tracking_active == True,
        Acquisition.tracking_number.isnot(None)
    ).all()

    for acq in active:
        carrier = get_carrier(acq.tracking_carrier)
        result = carrier.fetch_tracking(acq.tracking_number)

        if result.status != acq.tracking_status:
            notify_status_change(acq.user, acq, acq.tracking_status, result.status)
            acq.tracking_status = result.status

        # Deactivate 7 days after delivered
        if result.status == "Delivered":
            if not acq.tracking_delivered_at:
                acq.tracking_delivered_at = datetime.utcnow()
            elif (datetime.utcnow() - acq.tracking_delivered_at).days >= 7:
                acq.tracking_active = False

        acq.tracking_last_checked = datetime.utcnow()

    db.commit()
```

## Notification System

**Channels:**

- In-app: Always (stored in notifications table)
- Email: Via AWS SES (user preference)
- SMS: Via AWS SNS (user preference + phone required)

**Triggers:**

| Event | Message |
|-------|---------|
| Status change | "Your book '{title}' is now: {status}" |
| Delivered | "Your book '{title}' has been delivered!" |
| Exception | "Alert: '{title}' shipment exception: {detail}" |

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/users/me/notifications` | List notifications |
| PATCH | `/users/me/notifications/{id}` | Mark as read |
| PATCH | `/users/me/preferences` | Update notification prefs |
| POST | `/acquisitions/{id}/tracking/refresh` | Manual refresh |

## Frontend Components

1. **TrackingCard.vue** - Status display on acquisition detail
2. **NotificationBell.vue** - Header dropdown with unread badge
3. **NotificationPreferences.vue** - Settings page section

## Infrastructure (Terraform)

```hcl
# EventBridge rule for hourly polling
resource "aws_cloudwatch_event_rule" "tracking_poller" {
  name                = "${var.environment}-tracking-poller"
  schedule_expression = "rate(1 hour)"
}

# SNS topic for SMS notifications
resource "aws_sns_topic" "tracking_sms" {
  name = "${var.environment}-tracking-sms"
}

# IAM permissions for SES and SNS
```

## Implementation Plan

### Phase 1 (Parallel - 8 subagents)

| ID | Task | Files |
|----|------|-------|
| A | DB migrations & models | `alembic/`, `models/` |
| B | Carrier: UPS (move) | `carriers/base.py`, `carriers/ups.py` |
| C | Carrier: USPS | `carriers/usps.py` |
| D | Carrier: FedEx | `carriers/fedex.py` |
| E | Carrier: DHL | `carriers/dhl.py` |
| F | Carrier: Royal Mail | `carriers/royal_mail.py` |
| G | Carrier: Pitney Bowes | `carriers/pitney_bowes.py` |
| J | Terraform infra | `infra/terraform/` |

### Phase 2 (Parallel after A - 2 subagents)

| ID | Task | Files |
|----|------|-------|
| H | Notifications service | `notifications.py`, `routers/notifications.py` |
| I | Polling service | `tracking_poller.py`, `main.py` |

### Phase 3 (Parallel after H, I - 2 subagents)

| ID | Task | Files |
|----|------|-------|
| K | Frontend: TrackingCard | `components/TrackingCard.vue` |
| L | Frontend: Notifications | `components/NotificationBell.vue`, `NotificationPreferences.vue` |

## Testing Strategy

- Unit tests for each carrier (mock HTTP responses)
- Integration tests for polling service
- E2E test for notification flow
- TDD approach per session rules

## Decisions Log

| Question | Answer |
|----------|--------|
| Primary use case | Full feature set (status, delivery dates, notifications) |
| Notification channels | In-app + Email + SMS |
| Carrier API access | Public endpoints (no auth) |
| Polling frequency | Hourly |
| Tracking lifecycle | Auto: start on add, stop 7 days after delivered |
| Background job | EventBridge + Lambda |
| Architecture | Carrier Plugin pattern |
