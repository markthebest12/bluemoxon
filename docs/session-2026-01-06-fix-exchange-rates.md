# Session: Fix Hardcoded Exchange Rates (#861)

**Date:** 2026-01-06
**Issue:** #861 - orders.py has hardcoded 2024 currency exchange rates
**Branch:** `fix/exchange-rates-861`
**PR:** #893 (targeting staging)

---

## CRITICAL: Session Continuation Rules

### 1. ALWAYS Use Superpowers Skills

```
IF task involves implementation → use superpowers:brainstorming FIRST
IF task involves code changes → use superpowers:test-driven-development
IF task involves debugging → use superpowers:systematic-debugging
IF receiving feedback → use superpowers:receiving-code-review
IF completing work → use superpowers:verification-before-completion
```

**This is not optional. Even 1% chance a skill applies = invoke it.**

### 2. NEVER Use These Bash Patterns (Trigger Permission Prompts)

```bash
# BAD - NEVER DO:
# Comment lines before commands
command1 \
  --with-continuation    # Backslash continuations
$(command substitution)  # $(...) syntax
cmd1 && cmd2            # && chaining
cmd1 || cmd2            # || chaining
"string with !"         # ! in quoted strings
```

### 3. ALWAYS Use These Patterns

```bash
# GOOD - Simple single-line commands:
bmx-api GET /books
bmx-api PUT /admin/config '{"key": "value"}'
git status
poetry run pytest tests/test_orders_api.py -v

# Multiple commands = separate Bash tool calls, NOT chained
```

---

## Background

**Original Problem:**

- `backend/app/api/v1/orders.py:118` had hardcoded 2024 exchange rates
- GBP: 1.28 (stale), EUR: 1.10 (stale)
- Unknown currencies silently returned 1.0 with no logging
- AdminConfig DB table was source of truth but fallbacks were outdated

**Architecture (unchanged):**

1. Primary: DB lookup via AdminConfig table
2. Fallback: Hardcoded rates in code (safety net only)

---

## What Was Done

### Commit 1: Backend + Script

- Updated fallback rates to Jan 2026 values (GBP: 1.35, EUR: 1.17)
- Added warning logging when using fallback rates
- Created `scripts/update-exchange-rates.sh` to fetch live rates
- Added tests for logging behavior

### Commit 2: Frontend fetchLiveRate (REMOVED)

- Added fetchLiveRate() to call frankfurter.app from browser
- **PROBLEM**: Dead code (never wired up), external API risk, CORS issues

### Commit 3: Code Review Fixes

Addressed all P0/P1/P3 issues from code review:

| Issue | Fix |
|-------|-----|
| P0: Dead fetchLiveRate code | Removed entirely (YAGNI) |
| P0: Log spam (WARNING per request) | One-time warning per Lambda instance |
| P1: Script missing jq/bc checks | Added dependency validation |
| P1: Script missing auth check | Added API key existence check |
| P3: Loose test assertion | Changed to exact value assertions |
| P3: Stale date comment | Removed, clarified DB is source of truth |

---

## Current State

### Files Changed (Final)

| File | Status |
|------|--------|
| `backend/app/api/v1/orders.py` | One-time warning logging, updated fallbacks |
| `backend/app/api/v1/admin.py` | Updated fallbacks (1.35, 1.17) |
| `backend/tests/test_orders_api.py` | Tests for exact values + one-time warning |
| `frontend/src/composables/useCurrencyConversion.ts` | Updated DEFAULT_RATES only |
| `frontend/src/composables/__tests__/useCurrencyConversion.spec.ts` | Updated test values |
| `scripts/update-exchange-rates.sh` | Dependency + auth checks added |

### Tests

- Backend: 5 passing
- Frontend: 18 passing

### Staging DB

- Rates already updated via API: GBP=1.3513, EUR=1.1706

---

## Next Steps

### Immediate (Before Merge)

1. Push latest commit: `git push`
2. Wait for CI to pass on PR #893
3. User reviews PR before merge to staging

### After Staging Merge

1. Validate in staging environment
2. Create PR from staging → main
3. User reviews before production merge
4. After prod merge: `./scripts/update-exchange-rates.sh --prod`

### Future

- Consider periodic cron job to run update script
- Monitor CloudWatch for fallback warnings (indicates DB config missing)

---

## Key Decisions

1. **No external API from frontend** - Too risky (CORS, firewalls, no SLA)
2. **DB is source of truth** - Code fallbacks are emergency safety net only
3. **One-time warnings** - Log once per Lambda instance, not per request
4. **Script with guards** - Check dependencies and auth before making changes

---

## Usage

```bash
./scripts/update-exchange-rates.sh        # Update staging
./scripts/update-exchange-rates.sh --prod # Update production
```

Requires: `jq`, `bc`, `curl`, and valid API key at `~/.bmx/{env}.key`
