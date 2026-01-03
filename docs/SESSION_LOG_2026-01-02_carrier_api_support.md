# Session Log: Carrier API Support (#516)

**Date:** 2026-01-02
**Issue:** https://github.com/markthebest12/bluemoxon/issues/516
**Branch:** TBD (will create after design approval)

---

## Session Principles (MUST FOLLOW)

### 1. PR Review Gates
- **Before staging:** User reviews PR before merge
- **Before prod:** User reviews staging→main PR before merge
- No auto-merging - always wait for explicit approval

### 2. Bash Command Rules (Avoid Permission Prompts)
**NEVER use:**
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings

**ALWAYS use:**
- Simple single-line commands
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls

### 3. Superpowers Skills
- Use TDD (test-driven development)
- Use brainstorming for design
- Use writing-plans before implementation
- Use verification-before-completion
- Use code-reviewer before PRs

### 4. Session Continuity
- This log maintains context across chat compacting
- Update progress log after each significant action
- Document decisions and their rationale

---

## Context

**Current State:**
- UPS: Full API integration (public JSON endpoint, no auth)
- USPS, FedEx, DHL, Royal Mail, Parcelforce: URL generation only

**Goal:** Add API integration for carriers (updated priority):
1. USPS (most common for US)
2. FedEx (common for international)
3. DHL (common for UK/EU)
4. Royal Mail (UK domestic - user buys British books)
5. Pitney Bowes (eBay Global Shipping - trackpb.shipment.co, UPAA* tracking numbers)

## Brainstorming Session

### Question 1: Primary Use Case
Asked: What's the primary use case for carrier API integration?
- Status display
- Delivery date estimation
- Proactive notifications
- All of the above

**Answer:** All of the above - full tracking feature set

### Question 2: Notification Channels
Asked: How should users be notified of tracking updates?

**Answer:** All three channels:
- In-app (updates on acquisition detail page)
- Email (via SES)
- SMS/Text (via SNS or Twilio)
- User chooses preferences

### Question 3: Carrier API Access
Asked: How do you want to handle carrier API access?

**Answer:** Public endpoints (like current UPS implementation)
- No auth required, simpler to implement
- Trade-off: fragile, may break if carriers change endpoints
- Matches existing UPS pattern

### Question 4: Polling Frequency
Asked: How frequently should we poll for tracking updates?

**Answer:** Hourly
- ~24 checks/day per active shipment
- Good balance of freshness vs API load
- Enables same-day notification of status changes

### Question 5: Tracking Lifecycle
Asked: When should tracking start and stop?

**Answer:** Auto lifecycle
- Start when tracking number is added to acquisition
- Stop 7 days after "Delivered" status
- No manual intervention needed

### Question 6: Background Job Infrastructure
Asked: How should we run the hourly background polling job?

**Answer:** EventBridge + Lambda
- Scheduled rule triggers Lambda every hour
- Matches existing serverless architecture
- Simplest path, no new infrastructure patterns

### Approach Selection
Presented three approaches:
- A: Monolithic Extension (simple but coupled)
- B: Carrier Plugin Architecture (clean separation)
- C: Separate Microservice (overkill)

**Selected:** Approach B - Carrier Plugin Architecture

---

## Design (Sections)

### Section 1: Architecture Overview
**Status:** Approved

```
backend/app/services/
├── tracking.py              # Existing - keeps detect_carrier(), generate_url(), process_tracking()
├── tracking_poller.py       # NEW - hourly job orchestrator
├── notifications.py         # NEW - email/SMS/in-app dispatch
└── carriers/                # NEW - plugin directory
    ├── __init__.py          # Registry + base interface
    ├── base.py              # Abstract CarrierClient class
    ├── ups.py               # Existing UPS logic moved here
    ├── usps.py              # NEW
    ├── fedex.py             # NEW
    ├── dhl.py               # NEW
    ├── royal_mail.py        # NEW
    └── pitney_bowes.py      # NEW
```

New DB columns: tracking_status, tracking_last_checked, tracking_active, tracking_delivered_at

### Section 2: Carrier Plugin Interface
**Status:** Approved

- Base class: `CarrierClient` with `fetch_tracking()` and `can_handle()` methods
- `TrackingResult` dataclass: status, status_detail, estimated_delivery, delivered_at, location, error
- Registry: `get_carrier(name)` and `detect_and_get_carrier(tracking_number)`

### Section 3: Notification System
**Status:** Approved

- User preferences: notify_tracking_email, notify_tracking_sms, phone_number
- Triggers: status change, delivered, exception/delay
- Channels: SES (email), SNS (SMS), in-app (notifications table)
- New notifications table for in-app alerts

### Section 4: Polling System
**Status:** Approved

- EventBridge rule: rate(1 hour) triggers Lambda with action=poll_tracking
- Poller queries acquisitions where tracking_active=True
- For each: fetch status, check for changes, notify if changed
- Deactivate 7 days after "Delivered" status
- Returns stats: checked, changed, errors, deactivated

### Section 5: Carrier Implementations
**Status:** Approved

- Each carrier uses public endpoints (no auth, like existing UPS)
- Common interface: `fetch_tracking()` returns `TrackingResult`
- Pattern matching via `can_handle()` class method
- Priority: UPS (move) → DHL → USPS → FedEx → Royal Mail → Pitney Bowes

### Section 6: Frontend Changes
**Status:** Approved

- TrackingCard on acquisition detail: status, carrier, location, est. delivery
- NotificationBell in header with unread badge
- NotificationPreferences in user settings
- New endpoints: notifications list, mark read, preferences, manual refresh

### Section 7: Implementation Strategy
**Status:** Approved

- 12 parallel subagents across 3 phases
- Phase 1: DB/models, all 6 carriers, Terraform (parallel)
- Phase 2: Notifications, Polling (after models)
- Phase 3: Frontend components (after API)

---

## Design Complete
All sections approved. Design doc committed: `f2aa56c`

## Next Session Instructions

Start new chat with:
```
Read docs/plans/2026-01-02-carrier-api-support-design.md and implement using 12 parallel subagents per the Implementation Plan section. Use TDD. Create feature branch first.
```

**Subagents to spawn (Phase 1 - all parallel):**
- A: DB migrations & models
- B: Carrier: UPS (move existing)
- C: Carrier: USPS
- D: Carrier: FedEx
- E: Carrier: DHL
- F: Carrier: Royal Mail
- G: Carrier: Pitney Bowes
- J: Terraform infra

**Then Phase 2 (after A completes):**
- H: Notifications service
- I: Polling service

**Then Phase 3 (after H, I complete):**
- K: Frontend: TrackingCard
- L: Frontend: Notifications

---

## Progress Log

| Time | Action | Notes |
|------|--------|-------|
| Start | Read issue #516 | Low priority feature |
| Start | Read tracking.py | UPS has public API, others URL-only |
| Start | Created session log | Established workflow rules |
