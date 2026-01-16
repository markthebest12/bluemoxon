# Documentation Inventory

**Generated:** 2025-12-21
**Status:** Complete

## Summary

| Category | Count | Notes |
|----------|-------|-------|
| Top-level docs | 22 | Core documentation |
| Plan documents | 58 | Design and implementation docs |
| Session directories | 2 | Active work sessions |
| CLAUDE.md | 992 lines | Primary Claude reference (36KB) |

---

## Top-Level Documents (`docs/`)

### Core Architecture & Infrastructure

| Document | Lines | Purpose | Audience | Freshness | Notes |
|----------|-------|---------|----------|-----------|-------|
| `ARCHITECTURE.md` | ~60 | High-level system design | Dev | Current | Has basic architecture diagram, needs expansion |
| `INFRASTRUCTURE.md` | ~570 | AWS resource inventory, Terraform | Ops/Dev | Current | Very detailed, includes Mermaid diagrams |
| `DATABASE.md` | ~185 | Schema documentation | Dev | Current | Tables, indexes, full-text search |
| `CI_CD.md` | ~285 | GitHub Actions workflows | Dev/Ops | Current | Comprehensive pipeline docs |

### Operations & Deployment

| Document | Lines | Purpose | Audience | Freshness | Notes |
|----------|-------|---------|----------|-----------|-------|
| `DEPLOYMENT.md` | ~300 | Deploy procedures | Ops | Current | Manual deploy instructions |
| `ROLLBACK.md` | ~280 | Rollback procedures | Ops | Current | Lambda, S3, database rollback |
| `DATABASE_SYNC.md` | ~220 | Prod→Staging sync | Ops | Current | Lambda-based sync process |
| `PROD_MIGRATION_CHECKLIST.md` | ~585 | Terraform migration | Dev/Ops | Current | Detailed import procedures |

### API & Features

| Document | Lines | Purpose | Audience | Freshness | Notes |
|----------|-------|---------|----------|-----------|-------|
| `API.md` | ~140 | API overview | Dev | **STALE** | Outdated, references removed endpoints |
| `API_REFERENCE.md` | ~335 | Endpoint reference | Dev | **INCOMPLETE** | Missing many endpoints |
| `FEATURES.md` | ~175 | Feature catalog | All | Current | Good overview of 1.0 features |
| `BEDROCK.md` | ~245 | AI/Claude integration | Dev | Current | Good examples |

### Development

| Document | Lines | Purpose | Audience | Freshness | Notes |
|----------|-------|---------|----------|-----------|-------|
| `DEVELOPMENT.md` | ~170 | Local dev setup | Dev | **STALE** | References Docker not used |
| `PROMPTING_GUIDE.md` | ~405 | Claude session prompts | Dev | Current | Session handoff templates |
| `ROADMAP.md` | ~400 | Feature roadmap | All | **STALE** | Many items marked done, needs cleanup |

### Governance & Validation

| Document | Lines | Purpose | Audience | Freshness | Notes |
|----------|-------|---------|----------|-----------|-------|
| `INFRASTRUCTURE_GOVERNANCE.md` | ? | IaC policies | Dev/Ops | Current | Terraform requirements |
| `VALIDATION.md` | ? | Testing approach | Dev | Unknown | Need to review |
| `MIGRATION.md` | ? | Database migrations | Dev | Unknown | Need to review |
| `PERFORMANCE.md` | ? | Performance notes | Dev | Unknown | Need to review |

### Miscellaneous

| Document | Lines | Purpose | Audience | Freshness | Notes |
|----------|-------|---------|----------|-----------|-------|
| `225-LAMBDA-IMPORT-PLAN.md` | ? | Issue-specific | Dev | **ORPHAN** | Should be in plans/ |
| `FIX_CROSS_ACCOUNT_TERRAFORM_STATE_ACCESS.md` | ? | Troubleshooting | Ops | **ORPHAN** | Should be in plans/ |
| `EVAL_RUNBOOK_SCALING.md` | ? | Operations | Ops | Unknown | Need to review |

---

## Plan Documents (`docs/plans/`)

**Total: 58 files**

### Categories by Age

| Age | Count | Status |
|-----|-------|--------|
| < 7 days (recent) | 8 | Active/current |
| 7-30 days | 35 | Mostly completed |
| > 30 days | 15 | Archive candidates |

### Design Documents (Active Reference)

These contain architectural decisions still relevant:

| Document | Topic | Status |
|----------|-------|--------|
| `2025-12-10-acquisitions-dashboard-design.md` | Acquisitions workflow | Implemented |
| `2025-12-11-scoring-engine-design.md` | Investment scoring | Implemented |
| `2025-12-12-ebay-listing-integration-design.md` | eBay import | Implemented |
| `2025-12-12-wayback-archive-design.md` | Archive feature | Implemented |
| `2025-12-13-analysis-enrichment-design.md` | AI analysis | Implemented |

### Implementation Documents (Reference for Debugging)

Large implementation plans with code snippets:

| Document | Lines | Topic |
|----------|-------|-------|
| `2025-12-10-acquisitions-dashboard-implementation.md` | ~40K | Dashboard build |
| `2025-12-10-bedrock-analysis-implementation.md` | ~43K | Bedrock integration |
| `2025-12-11-scoring-engine-implementation.md` | ~48K | Scoring system |
| `2025-12-12-ebay-listing-implementation.md` | ~45K | eBay import |
| `2025-12-15-eval-runbook-implementation.md` | ~57K | Evaluation workflows |
| `2025-12-16-fmv-accuracy-implementation.md` | ~27K | FMV calculations |

### Archive Candidates (> 30 days, completed)

| Document | Topic | Recommendation |
|----------|-------|----------------|
| `2024-12-09-victorian-ui-design.md` | UI theming | Archive |
| `2025-12-08-cognito-sync-implementation.md` | Auth sync | Archive |
| `2025-12-08-frontend-config-drift-design.md` | Config validation | Archive |
| `2025-12-08-staging-auth-investigation.md` | Debug notes | Archive |
| `2025-12-08-terraform-conformance-review.md` | IaC review | Archive |
| `2025-12-09-disaster-recovery-design.md` | DR planning | Keep (reference) |
| `2025-12-09-sequence-reset-design.md` | DB fix | Archive |

---

## Session Directories

| Directory | Purpose | Status |
|-----------|---------|--------|
| `session-2025-12-21-documentation-review/` | This review | Active |
| `session-2025-12-21-theming-print/` | Victorian theming work | Recent |

---

## CLAUDE.md Analysis

**Current Size:** 992 lines (~36KB)

### Content Breakdown (Estimated)

| Section | Purpose | Lines | Candidate for Move |
|---------|---------|-------|-------------------|
| Bash Command Formatting | Quick ref | ~40 | Keep |
| BMX API Calls | Quick ref | ~20 | Keep |
| Permission Patterns | Quick ref | ~40 | Keep |
| CI/CD Workflow Requirements | Procedures | ~80 | → CI_CD.md |
| Staging-First Workflow | Procedures | ~60 | → DEPLOYMENT.md |
| Branching Strategy | Procedures | ~40 | → CI_CD.md |
| Staging Environment | Details | ~80 | → Dedicated doc |
| Version System | Reference | ~30 | Keep (short) |
| Database Migrations | Procedures | ~20 | → DATABASE.md |
| Terraform Guidelines | Procedures | ~200 | → INFRASTRUCTURE.md |
| Troubleshooting | Procedures | ~50 | → OPERATIONS.md |
| Project Structure | Reference | ~30 | Keep |
| AWS Resources | Reference | ~20 | → INFRASTRUCTURE.md |
| Quick Commands | Quick ref | ~40 | Keep |

### Reduction Potential

| Current | Target | Method |
|---------|--------|--------|
| 992 lines | ~400 lines | Move procedures, keep quick refs |
| ~36KB | ~15KB | Link to detailed docs |

---

## Identified Issues

### Redundancies

| Topic | Found In | Recommendation |
|-------|----------|----------------|
| Terraform commands | CLAUDE.md + INFRASTRUCTURE.md | Consolidate to INFRASTRUCTURE.md |
| Deploy procedures | CLAUDE.md + DEPLOYMENT.md + CI_CD.md | Consolidate to DEPLOYMENT.md |
| Staging environment | CLAUDE.md + multiple docs | Create dedicated STAGING.md |
| Rollback procedures | CLAUDE.md + ROLLBACK.md | Keep in ROLLBACK.md only |
| Cognito configuration | CLAUDE.md + PROD_MIGRATION.md | Consolidate |

### Orphan Documents

| Document | Issue | Action |
|----------|-------|--------|
| `225-LAMBDA-IMPORT-PLAN.md` | Issue-specific, in wrong location | Move to plans/ or archive |
| `FIX_CROSS_ACCOUNT_TERRAFORM_STATE_ACCESS.md` | Troubleshooting note | Move to plans/ or archive |

### Stale Content

| Document | Issue | Action |
|----------|-------|--------|
| `API.md` | References old endpoints | Update or merge with API_REFERENCE.md |
| `DEVELOPMENT.md` | References Docker compose not used | Update for current workflow |
| `ROADMAP.md` | Many completed items | Clean up, move done items |

### Missing Documentation

| Topic | Current State | Needed |
|-------|---------------|--------|
| API endpoints | Partial in API_REFERENCE.md | Full endpoint catalog with examples |
| Retry logic (Bedrock) | Not documented | Sequence diagram of retry/backoff |
| Analysis pipeline | Scattered in plans | Consolidated flow diagram |
| Error handling | Not documented | Error codes and troubleshooting |
| Monitoring/Alerts | Mentioned in INFRASTRUCTURE.md | Dedicated runbook |

---

## Cross-Reference Map

Documents that reference each other (for consolidation planning):

```text
CLAUDE.md
├── References: INFRASTRUCTURE.md, CI_CD.md, DEPLOYMENT.md
├── Duplicates content from: All of the above
└── Should link to instead of duplicate

INFRASTRUCTURE.md
├── Self-contained (good)
├── Has Mermaid diagrams (good)
└── Referenced by: CLAUDE.md, PROD_MIGRATION_CHECKLIST.md

CI_CD.md
├── Self-contained (good)
├── Has ASCII diagram
└── Referenced by: CLAUDE.md

DEPLOYMENT.md
├── Overlaps with: CI_CD.md (deploy procedures)
├── Referenced by: CLAUDE.md
└── Consider: Merge CI_CD.md into DEPLOYMENT.md?

API.md + API_REFERENCE.md
├── Overlap significantly
└── Consider: Merge into single API.md
```

---

## Next Steps

Phase 2 will audit the codebase to identify:

1. Features not documented
2. API endpoints missing from API_REFERENCE.md
3. Resiliency patterns (retry logic, error handling) needing diagrams
4. Scripts and utilities without documentation
