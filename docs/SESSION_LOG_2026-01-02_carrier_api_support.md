# Session Log: Carrier API Support (#516)

**Date**: 2026-01-02 - 2026-01-03
**Issue**: #516

---

## CRITICAL SESSION RULES (MUST FOLLOW)

### 1. Superpowers Skills - USE AT ALL STAGES
**Invoke relevant skills BEFORE any response or action.** Even 1% chance = invoke.
- `superpowers:brainstorming` - Before any creative/feature work
- `superpowers:test-driven-development` - Before writing implementation code
- `superpowers:verification-before-completion` - Before claiming work is done
- `superpowers:systematic-debugging` - Before proposing fixes for any bug
- `superpowers:code-reviewer` - After significant code changes

**RED FLAGS - If you think these, STOP and invoke the skill:**
- "This is simple, I'll just..."
- "Let me quickly fix this..."
- "I'm confident this works..."

### 2. Bash Command Rules (AVOID PERMISSION PROMPTS)
**NEVER use:**
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings

**ALWAYS use:**
- Simple single-line commands
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls (no permission prompts)

### 3. PR Review Gates
- User reviews PR before staging merge
- User reviews staging→main PR before prod merge
- No auto-merging without explicit approval

---

## Current Status (as of 2026-01-03 chat compaction #3)

### COMPLETED THIS SESSION

| Task | Status | Evidence |
|------|--------|----------|
| PR #777 merged to staging | DONE | Commit 5119934 |
| PR #778 closed | DONE | Architecturally replaced with main→staging sync |
| Main→staging merged | DONE | Commit 1674b97 (resolved 4 conflicts) |
| Staging deploy | SUCCESS | Run 20682327273 |
| Staging API health | HEALTHY | `/health/deep` all checks pass |
| Migration d3b3c3c4dd80 | RAN | `previous_version: "d3b3c3c4dd80"` |
| Backfill tracking_active | COMPLETE | UPDATE ran successfully |

### CARRIER API TESTING RESULTS

Tested all 3 carrier types in staging. **APIs are being called but returning errors:**

| Carrier | Book ID | Error | Root Cause |
|---------|---------|-------|------------|
| USPS | 504 | HTTP 302 | API endpoint changed or auth needed |
| UPS | 494 | Timeout | Connection issue or API slow |
| Royal Mail | 525 | HTTP 403 | Blocked/auth required |

**Lambda log evidence:**
```
USPS API HTTP error: 302
UPS API timeout: The read operation timed out
GET https://www.royalmail.com/track-your-item/api/tracking/LO403920817GB "HTTP/1.1 403 Forbidden"
```

**This is expected behavior** - the code correctly returns "Unknown" when API calls fail. The issue is carrier API configurations, not the code.

**Contributing factors:**
1. Tracking numbers may be old/expired (books ordered Dec 2025)
2. Carrier APIs may need updated credentials
3. Royal Mail may be blocking non-UK IP addresses

---

## Next Steps (Priority Order)

### 1. Fix Carrier API Configurations
Investigate and fix each carrier:

**USPS (HTTP 302):**
- Check if API endpoint changed
- Verify USPS_USER_ID environment variable is set
- Test with fresh tracking number

**UPS (Timeout):**
- Check UPS_CLIENT_ID and UPS_CLIENT_SECRET
- Verify network connectivity from Lambda
- Consider increasing timeout

**Royal Mail (HTTP 403):**
- May need API key registration
- May be blocking AWS IP ranges
- Consider using proxy or different approach

### 2. Test Notification Flow
After carrier APIs work:
1. Add phone number via staging frontend settings
2. Enable SMS notifications
3. Trigger status change to receive notification

### 3. Promote to Production
Create staging→main PR after carrier APIs verified working.

---

## Files Modified in This Session

### Merged to Staging
- `backend/alembic/versions/d3b3c3c4dd80_backfill_tracking_active_for_in_transit_.py`
- `backend/alembic/versions/w6789012wxyz_add_carrier_api_support.py`
- `backend/tests/test_carrier_api_models.py`
- `backend/app/api/v1/health.py`

### Merge Conflicts Resolved (main→staging)
- `backend/alembic/versions/w6789012wxyz_add_carrier_api_support.py` (kept note comment)
- `backend/app/api/v1/health.py` (kept migration registration)
- `backend/tests/test_carrier_api_models.py` (kept TestDataMigrationBehavior class)
- `docs/SESSION_LOG_2026-01-02_carrier_api_support.md` (kept staging version)

---

## Background Context

### Issue #516 - Carrier API Support
- Multiple carriers: UPS, USPS, FedEx, DHL, Royal Mail, Pitney Bowes
- Hourly polling via EventBridge + Lambda
- Notifications: in-app + email (SES) + SMS (SNS)
- Deployed to prod (PR #773), staging now synced

### The Backfill Problem (RESOLVED)
Migration `w6789012wxyz` added `tracking_active` column defaulting to `false`. Migration `d3b3c3c4dd80` backfills `tracking_active=true` for existing IN_TRANSIT books with tracking numbers.

### The defusedxml Problem (RESOLVED)
Staging was missing defusedxml. Fixed by merging main→staging instead of PR #778.

---

## API Endpoints for Testing

```bash
# Refresh tracking for a specific book
bmx-api POST /books/504/tracking/refresh

# Check in-transit books
bmx-api GET '/books?status=IN_TRANSIT'

# Check staging health
curl -s https://staging.api.bluemoxon.com/api/v1/health/deep

# View Lambda logs (use timestamp, not command substitution)
# First get timestamp: date +%s000
# Then use that value directly
AWS_PROFILE=bmx-staging aws logs filter-log-events --log-group-name /aws/lambda/bluemoxon-staging-api --filter-pattern "USPS" --start-time 1767472516000 --limit 10
```

---

## Carrier Implementation Files

| Carrier | File | API Used |
|---------|------|----------|
| USPS | `app/services/carriers/usps.py` | USPS Web Tools XML API |
| UPS | `app/services/carriers/ups.py` | UPS Tracking API |
| Royal Mail | `app/services/carriers/royal_mail.py` | Royal Mail public tracking |
| FedEx | `app/services/carriers/fedex.py` | FedEx Track API |
| DHL | `app/services/carriers/dhl.py` | DHL Unified Tracking API |
| Pitney Bowes | `app/services/carriers/pitney_bowes.py` | Pitney Bowes Tracking API |

---

## In-Transit Books with Tracking (Staging)

15 books have tracking numbers:
- 13 USPS
- 1 UPS
- 1 Royal Mail

Example book IDs for testing:
- USPS: 504, 497, 514, 528
- UPS: 494
- Royal Mail: 525
