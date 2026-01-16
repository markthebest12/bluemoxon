# Deploy Path-Based Filtering Design

**Issue:** #907
**Date:** 2026-01-06
**Status:** Approved

## Summary

Add path-based filtering to the deploy workflow (`deploy.yml`) so only changed components are built and deployed, reducing deploy time by 40-65% for partial changes.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Layer handling | Skip entirely when backend unchanged | Fastest, cleanest |
| Deploy granularity | Per-Lambda jobs (7+ jobs) | Maximum parallelism |
| Smoke tests | Always run full suite | Catches regressions, simpler |
| Force override | Boolean `force_full_deploy` input | Emergency deploys, workflow changes |
| Path categories | Backend/Frontend/Scraper only | Keep it simple |

## Architecture

```text
push/workflow_dispatch
    │
    ▼
┌─────────┐
│   CI    │
└────┬────┘
     │
     ▼
┌──────────┐
│ changes  │ ◄── dorny/paths-filter
└────┬─────┘
     │
     ├─────────────────────────────────────────────┐
     │                                             │
     ▼                                             ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ build-layer │  │build-backend│  │build-frontend│ │build-scraper│
│ (if backend)│  │ (if backend)│  │(if frontend) │ │ (if scraper)│
└──────┬──────┘  └──────┬──────┘  └──────┬───────┘ └──────┬──────┘
       │                │                │                │
       └────────┬───────┘                │                │
                │                        │                │
     ┌──────────┼──────────┬─────────────┼────────────────┤
     ▼          ▼          ▼             ▼                ▼
  [6 Lambda deploy jobs in parallel]  [frontend]      [scraper]
                │                        │                │
                └────────────────────────┴────────────────┘
                                  │
                                  ▼
                          ┌──────────────┐
                          │  migrations  │
                          └──────┬───────┘
                                 │
                                 ▼
                          ┌──────────────┐
                          │  smoke-test  │
                          └──────┬───────┘
                                 │
                                 ▼
                          ┌──────────────┐
                          │create-release│
                          └──────────────┘
```

## Implementation Tasks (Parallelizable)

### Task 1: Add changes job + workflow_dispatch input

- Add `dorny/paths-filter@v3` job after CI
- Add `force_full_deploy` boolean input to workflow_dispatch
- Outputs: backend, frontend, scraper

### Task 2: Make build jobs conditional

- Add `changes` to needs for: build-layer, build-backend, build-frontend, build-scraper
- Add if conditions checking path filter outputs + force_full_deploy

### Task 3: Split deploy job into deploy-api-lambda

- Extract API Lambda deployment steps
- Add OIDC auth, artifact download, layer handling
- Output: api_lambda_version

### Task 4: Split deploy job into deploy-worker-lambda

- Extract Analysis Worker Lambda deployment steps
- Same pattern as Task 3

### Task 5: Split deploy job into deploy-eval-worker-lambda

- Extract Eval Runbook Worker Lambda deployment steps

### Task 6: Split deploy job into deploy-cleanup-lambda

- Extract Cleanup Lambda deployment steps

### Task 7: Split deploy job into deploy-tracking-dispatcher-lambda

- Extract Tracking Dispatcher Lambda deployment steps

### Task 8: Split deploy job into deploy-tracking-worker-lambda

- Extract Tracking Worker Lambda deployment steps

### Task 9: Split deploy job into deploy-scraper-lambda

- Extract Scraper Lambda deployment steps
- Conditional on scraper changes

### Task 10: Split deploy job into deploy-frontend

- Extract frontend S3 sync + CloudFront invalidation steps
- Conditional on frontend changes

### Task 11: Create run-migrations job

- Extract migration steps from deploy job
- Conditional on backend changes
- Depends on deploy-api-lambda

### Task 12: Update smoke-test job dependencies

- Add all deploy jobs to needs
- Keep full test suite (no conditional tests)
- Use always() to run after skipped jobs

### Task 13: Update create-release job

- Depends on smoke-test
- No changes needed to logic

## Acceptance Criteria

- [ ] Frontend-only changes skip all Lambda builds/deploys
- [ ] Backend-only changes skip frontend build/deploy
- [ ] Scraper-only changes only rebuild/deploy scraper
- [ ] Full stack changes work as before
- [ ] `workflow_dispatch` can force full deploy
- [ ] Smoke tests run full suite regardless of changes
- [ ] Deploy time reduced by 40-60% for partial deploys

## Related

- #906 - CI path-based filtering
- PR #892, #901 - Parallel Lambda deploys
