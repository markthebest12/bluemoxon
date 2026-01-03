# Session Log: Carrier API Support (#516)

**Date**: 2026-01-02
**Branch**: feat/carrier-api-support
**Issue**: #516

## Summary

Implementing carrier API support for tracking shipments across multiple carriers (UPS, USPS, FedEx, DHL, Royal Mail, Pitney Bowes) with automated polling and user notifications.

## Implementation Phases

### Phase 1: Backend Foundation (COMPLETED)

**Tasks A-G, J executed in parallel:**

| Task | Description | Files | Tests |
|------|-------------|-------|-------|
| A | DB migrations | `notification.py`, `user.py`, `book.py`, migration | 25 |
| B | UPS carrier | `carriers/base.py`, `carriers/ups.py` | 28 |
| C | USPS carrier | `carriers/usps.py` | 25 |
| D | FedEx carrier | `carriers/fedex.py` | 21 |
| E | DHL carrier | `carriers/dhl.py` | 17 |
| F | Royal Mail carrier | `carriers/royal_mail.py` | 18 |
| G | Pitney Bowes carrier | `carriers/pitney_bowes.py` | 19 |
| J | Terraform | `modules/notifications/`, EventBridge rules | validated |

**Key Components:**
- `TrackingResult` dataclass for standardized responses
- `CarrierClient` abstract base class with registry pattern
- `get_carrier()` and `detect_and_get_carrier()` for carrier lookup
- New fields: `tracking_active`, `tracking_delivered_at` on Book
- New fields: `notify_tracking_email`, `notify_tracking_sms`, `phone_number` on User
- New `Notification` model with user/book relationships

### Phase 2: Services (COMPLETED)

**Tasks H, I executed in parallel:**

| Task | Description | Files | Tests |
|------|-------------|-------|-------|
| H | Notifications service | `notifications.py`, router, SES/SNS integration | 31 |
| I | Polling service | `tracking_poller.py`, Lambda handler for EventBridge | 20 |

**Notifications Service:**
- `create_in_app_notification()` - Creates in-app notifications
- `send_email_notification()` - Sends via AWS SES (if enabled)
- `send_sms_notification()` - Sends via AWS SNS (if enabled)
- `send_tracking_notification()` - Main dispatcher
- API endpoints: `GET/PATCH /users/me/notifications`, `PATCH /users/me/preferences`

**Polling Service:**
- `poll_all_active_tracking()` - Polls all active tracking (for EventBridge)
- `refresh_single_book_tracking()` - Manual refresh for single book
- `notify_status_change()` - Creates notifications on status changes
- Auto-deactivates tracking 7 days after delivery
- Lambda handler routes between HTTP and EventBridge events

### Phase 3: Frontend (IN PROGRESS)

**Tasks K, L executing in parallel:**

| Task | Description | Files |
|------|-------------|-------|
| K | TrackingCard component | `components/TrackingCard.vue` |
| L | Notifications UI | `components/NotificationBell.vue`, `NotificationPreferences.vue` |

## Files Created

### Backend
- `backend/app/models/notification.py`
- `backend/app/services/carriers/base.py`
- `backend/app/services/carriers/ups.py`
- `backend/app/services/carriers/usps.py`
- `backend/app/services/carriers/fedex.py`
- `backend/app/services/carriers/dhl.py`
- `backend/app/services/carriers/royal_mail.py`
- `backend/app/services/carriers/pitney_bowes.py`
- `backend/app/services/carriers/__init__.py`
- `backend/app/services/notifications.py`
- `backend/app/services/tracking_poller.py`
- `backend/app/api/v1/notifications.py`
- `backend/alembic/versions/w6789012wxyz_add_carrier_api_support.py`

### Tests
- `backend/tests/test_carrier_api_models.py`
- `backend/tests/services/carriers/test_*.py` (6 files)
- `backend/tests/services/test_notifications.py`
- `backend/tests/services/test_tracking_poller.py`
- `backend/tests/routers/test_notifications_router.py`

### Infrastructure
- `infra/terraform/modules/notifications/main.tf`
- `infra/terraform/modules/notifications/variables.tf`
- `infra/terraform/modules/notifications/outputs.tf`

## Files Modified

- `backend/app/models/user.py` - Added notification preferences
- `backend/app/models/book.py` - Added tracking_active, tracking_delivered_at
- `backend/app/models/__init__.py` - Added Notification export
- `backend/app/api/v1/__init__.py` - Added notifications router
- `backend/app/api/v1/books.py` - Updated tracking refresh endpoint
- `backend/app/main.py` - Added EventBridge handler routing
- `backend/app/config.py` - Added notification_from_email setting

## Test Results

- Phase 1: ~153 tests passing
- Phase 2: 51 additional tests (31 notifications + 20 polling)
- All linting passing

## Additional Changes

### Data Migration for Existing In-Transit Books
Since the carrier API migration already ran in production without the backfill,
created a **separate migration** (`d3b3c3c4dd80_backfill_tracking_active_for_in_transit_.py`):
- Sets `tracking_active = true` for existing books where:
  - `tracking_number IS NOT NULL`
  - `status = 'IN_TRANSIT'`
  - `tracking_active = false`
- This ensures existing in-transit shipments are picked up by the hourly polling job

Added tests in `TestDataMigrationBehavior`:
- `test_in_transit_books_with_tracking_should_be_active`
- `test_delivered_books_should_not_be_active`
- `test_books_without_tracking_should_not_be_active`
- `test_migration_activates_correct_subset`

**Migration file:** `alembic/versions/d3b3c3c4dd80_backfill_tracking_active_for_in_transit_.py`

## Next Steps

1. Wait for Phase 3 frontend agents to complete
2. Run full test suite
3. Create PR for user review (NOT auto-merge - user requested review)
