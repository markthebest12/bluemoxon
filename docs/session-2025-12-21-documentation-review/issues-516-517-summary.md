# Issues #516 and #517 - Work Summary

## Overview

These issues were discovered during the documentation review session on 2025-12-21. Both represent TODOs in the codebase that were converted to trackable GitHub issues.

---

## Issue #516: Add Carrier API Support for USPS, FedEx, DHL

**Status:** Open
**Priority:** Low
**Labels:** enhancement

### Background

The tracking service (`backend/app/services/tracking.py`) provides shipment tracking functionality. Currently, only UPS has full API integration for live tracking status.

### Current State

| Carrier | Integration Level | Location |
|---------|------------------|----------|
| UPS | Full API (lines 144-196) | `fetch_ups_tracking()` |
| USPS | URL generation only | lines 60-77 |
| FedEx | URL generation only | lines 60-77 |
| DHL | URL generation only | lines 60-77 |
| Royal Mail | URL generation only | lines 60-77 |
| Parcelforce | URL generation only | lines 60-77 |

**Code Location:** `backend/app/services/tracking.py:218`

```python
# Current fallback behavior (line 218)
# TODO: Add support for USPS, FedEx, etc.
return TrackingInfo(
    status="Check carrier website",
    last_checked=datetime.utcnow(),
    error=f"Live tracking not yet supported for {carrier}",
)
```

### Next Steps

1. **Research carrier APIs:**
   - USPS Web Tools API (free, requires registration)
   - FedEx Track API (developer account required)
   - DHL Shipment Tracking API

2. **Implementation priority:**
   - USPS first (most common for US shipments)
   - FedEx second (international shipping)
   - DHL third (UK/EU shipping)

3. **Pattern to follow:** Copy the UPS integration pattern (lines 144-196)

---

## Issue #517: Implement Set Completion Detection

**Status:** Open
**Priority:** Medium
**Labels:** enhancement

### Background

The tiered scoring system awards bonus points when a book would complete an incomplete set in the collection. Currently, this detection is hardcoded to `False`.

### Current State

**Code Location:** `backend/app/services/eval_generation.py:555`

```python
tiered_strategic_fit_score = calculate_strategic_fit_score(
    publisher_matches_author_requirement=publisher_matches,
    author_book_count=author_book_count,
    completes_set=False,  # TODO: Implement set completion detection
)
```

**Also hardcoded in:** `backend/app/services/scoring.py:628`

### Impact

- Missing +20 points from `STRATEGIC_COMPLETES_SET` bonus
- Affects Strategic Fit Score calculation
- Multi-volume acquisitions not properly scored

### Implementation Approach

1. **Query existing collection** for matching author/title patterns
2. **Detect volume numbering** (Vol. 1, Vol. 2, etc.)
3. **Check if new book completes** a partial set
4. **Pass result** to `calculate_strategic_fit_score()`

### Related Code

- `tiered_scoring.py:153` - Where bonus is applied if `completes_set=True`
- `scoring.py:252` - Legacy scoring also uses this flag (+25 points)

---

## Superpowers Skills Reminder

When implementing these features, use the appropriate skill chains:

### For New Feature Implementation

```
brainstorming → using-git-worktrees → writing-plans → subagent-driven-development
```

### For Writing Tests

```
test-driven-development → condition-based-waiting → testing-anti-patterns
```

### Key Skills

| Skill | When to Use |
|-------|-------------|
| `brainstorming` | Before writing any code - refine requirements |
| `writing-plans` | Create detailed implementation tasks |
| `test-driven-development` | Write test first, watch it fail, then implement |
| `verification-before-completion` | Before claiming work is done |

---

## Bash Command Rules (CRITICAL)

**NEVER use these - they trigger permission prompts:**
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings

**ALWAYS use:**
- Simple single-line commands
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls (no permission prompts)

### Examples

```bash
# BAD - will prompt for permissions:
# Check the tracking service
poetry run pytest backend/tests/services/test_tracking.py && echo "done"

# GOOD - separate calls:
poetry run pytest backend/tests/services/test_tracking.py
```

```bash
# BAD - command substitution:
aws logs filter-log-events --start-time $(date +%s000)

# GOOD - calculate value first, use simple command:
aws logs filter-log-events --start-time 1734789600000
```

---

## Related Documentation

- [Session README](./README.md) - Full documentation review session
- [Issues Created](./issues-created.md) - All issues from this session
- [Gap Analysis](./gap-analysis.md) - Documentation gaps identified
