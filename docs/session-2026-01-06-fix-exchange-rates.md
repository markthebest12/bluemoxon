# Session: Fix Hardcoded Exchange Rates (#861)

**Date:** 2026-01-06
**Issue:** #861 - orders.py has hardcoded 2024 currency exchange rates

## Problem
`backend/app/api/v1/orders.py` line 118 has hardcoded exchange rates from 2024:
- GBP: 1.28 (actual ~1.35)
- EUR: 1.10 (actual ~1.17)
- Unknown currencies silently return 1.0

## Solution Implemented

### Approach Chosen: Admin API + Logging + Script
1. **Immediate fix**: Updated staging rates via admin API
2. **Script**: Created `scripts/update-exchange-rates.sh` to fetch live rates
3. **Logging**: Added warning logs when using fallback rates
4. **Updated fallbacks**: Changed hardcoded values to Jan 2026 rates

### Changes Made
| File | Change |
|------|--------|
| `backend/app/api/v1/orders.py` | Added warning logging, updated fallback rates |
| `backend/app/api/v1/admin.py` | Updated fallback rates |
| `backend/tests/test_orders_api.py` | Added tests for logging behavior |
| `scripts/update-exchange-rates.sh` | New script to fetch live rates |

### TDD Cycle
1. **RED**: Wrote failing tests for logging behavior
2. **GREEN**: Implemented logging, tests pass
3. **REFACTOR**: Updated other fallback locations

## Session Progress

### Phase 1: Brainstorming & Design
- [x] Understand current code
- [x] Choose approach (Admin API + logging + script)
- [x] Create design doc (this file)

### Phase 2: TDD Implementation
- [x] Write failing tests
- [x] Implement solution
- [x] Verify tests pass

### Phase 3: PR & Review
- [ ] Create PR to staging
- [ ] Review before merge
- [ ] Deploy to staging
- [ ] Validate
- [ ] PR to main
- [ ] Review before prod

## Usage

Update rates periodically:
```bash
./scripts/update-exchange-rates.sh        # Staging
./scripts/update-exchange-rates.sh --prod # Production
```

## Notes
- Live rates fetched from frankfurter.app (free, no auth)
- Staging updated: GBP=1.3513, EUR=1.1706

## Additional Feature: Live Rate Fetch on Currency Selection

Added hybrid approach for frontend:
1. When user selects GBP/EUR, fetch live rate from frankfurter.app
2. If external API fails, fall back to backend `/admin/config`
3. If both fail, use DEFAULT_RATES

### New Function: `fetchLiveRate(currency)`
- Added to `useCurrencyConversion` composable
- Call on currency change to get real-time rates
- TDD: 5 new tests added

### PR #893 Changes
**Commit 1**: Backend logging + script + fallback updates
**Commit 2**: Frontend fetchLiveRate with hybrid fallback

