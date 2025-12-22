# Session: Admin Config Dashboard (#529)

**Date:** 2025-12-21
**Issue:** [#529](https://github.com/markthebest12/bluemoxon/issues/529)
**Status:** Design complete, ready for implementation

---

## Summary

Expand `/admin/config` from currency rates editor to comprehensive admin dashboard with:
- **Settings tab** - Currency rates (editable)
- **System Status tab** - Health, versions, cold start indicator
- **Scoring Config tab** - All tiered_scoring.py constants
- **Entity Tiers tab** - Authors/Publishers/Binders by tier (1-3)

## Key Decisions (via brainstorming)

| Decision | Choice |
|----------|--------|
| Page structure | Tabbed interface (4 tabs) |
| Data refresh | Manual only (button) |
| Entity display | Three separate tables, 3-column grid |
| Scoring detail | Full breakdown with key tunables highlighted |
| System status | Health + versions + models (no Lambda metrics) |
| API design | Single aggregate endpoint |
| Error handling | Alert banner + inline status badges |
| Cold start | Show indicator when detected |

## Navigation Change

Profile dropdown menu:
```
Profile
Config          <- NEW (editors + admins)
Admin Settings  (admins only)
Sign Out
```

## Files

- **Design:** `docs/plans/2025-12-21-admin-config-dashboard-design.md`
- **Issue:** #529

## Next Steps

1. Use superpowers:using-git-worktrees to create isolated workspace
2. Use superpowers:writing-plans to create detailed implementation plan
3. Use superpowers:subagent-driven-development to execute

---

*Last updated: 2025-12-21 (Design complete)*
