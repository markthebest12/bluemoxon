# GitHub Issues Created During Documentation Review

## Summary

| Category | Count |
|----------|-------|
| Unfinished Implementations (TODOs) | 2 |
| Missing Features (ROADMAP) | 4 |
| Pre-existing Open Issues | 8 |
| **Total New Issues Created** | **2** |

---

## Issues Created This Session

### Unfinished Implementations (TODOs in Code)

| Issue | Location | Description |
|-------|----------|-------------|
| #516 | `backend/app/services/tracking.py:218` | Add carrier API support for USPS, FedEx, DHL |
| #517 | `backend/app/services/eval_generation.py:105` | Implement set completion detection |

---

## Pre-existing Open Issues (Not Created, Already Tracked)

These issues existed before the documentation review:

| Issue | Title | Age | Notes |
|-------|-------|-----|-------|
| #507 | Add CI/CD smoke tests and regression tests | 1 day | In progress (separate session) |
| #506 | Re-analyze books for provenance detection | 1 day | In progress (separate session) |
| #477 | Schedule RDS Aurora pause for staging | 2 days | Infrastructure optimization |
| #476 | Add Bedrock VPC endpoint | 2 days | Eliminate NAT Gateway dependency |
| #299 | Add smoke test for eBay URL extract | 7 days | Testing gap |
| #229 | Eliminate Terraform enable_* divergence | 11 days | Infrastructure tech debt |
| #191 | Phase 4: Cleanup admin panel UI | 9 days | UI cleanup |
| #190 | Phase 4: Admin cleanup API endpoint | 9 days | API cleanup |
| #189 | Phase 4: Cleanup Lambda for stale items | 9 days | Infrastructure cleanup |
| #166 | Migrate to Tailwind CSS v4 | 11 days | Frontend upgrade |

---

## ROADMAP.md Uncommitted Items (Not Creating Issues)

These are tracked in ROADMAP.md but not as GitHub issues:

| Feature | Priority | Status |
|---------|----------|--------|
| Add Images to Insurance Report | Low | Not started |
| Audit Logging | Low | Not started |
| SNS Notifications | Low | Planned |
| Deployment Notifications | Low | Planned |

**Decision:** These are low-priority features tracked in ROADMAP.md. No GitHub issues needed until prioritized.

---

## Review Gap Analysis

### What the Documentation Review Found

- 65 documentation gaps (undocumented features)
- 4 high-priority Mermaid diagrams created
- 3 Terraform module READMEs created
- 12 obsolete documents archived
- CLAUDE.md reduced from 36KB to 19.4KB

### What the Review Initially Missed

1. **Open GitHub issues** - Not cross-referenced against documentation
2. **TODOs in code** - Found but no issues created
3. **ROADMAP.md status** - Uncommitted items not flagged
4. **Recent plans completion status** - No verification of implementation

### Lessons Learned

- Future doc reviews should include GitHub issue audit
- TODOs found should immediately become issues
- ROADMAP.md should be reviewed for stale uncommitted items
