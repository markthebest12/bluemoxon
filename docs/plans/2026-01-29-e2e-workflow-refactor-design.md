# E2E Workflow Refactor + Timeout Fix

**Date:** 2026-01-29
**Issues:** #1539, #1559
**Branch:** `refactor/e2e-workflow`

## Problem

1. **YAML duplication (#1539):** 9 jobs in `e2e.yml` with near-identical step sequences (~180 lines of copy-paste). Any change requires updating 9 places.
2. **Timeout (#1559):** 184 social-circles tests run on a single Playwright worker, consistently timing out at the 15-minute job limit.

## Design

### Reusable Workflow

Extract a called workflow `.github/workflows/e2e-suite.yml` with inputs:

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `suite-name` | string | required | Artifact name and display label |
| `test-pattern` | string | required | Playwright test glob |
| `browsers` | string | `"chromium webkit"` | Browsers to install |
| `playwright-args` | string | `""` | Extra Playwright CLI args |
| `env-vars` | string | `""` | Extra environment variables |
| `timeout` | number | `15` | Job timeout in minutes |

The reusable workflow contains the 7 shared steps: checkout, setup-node, npm ci, install Playwright browsers, AWS OIDC credentials, run tests, upload artifacts on failure.

Each suite in `e2e.yml` becomes a ~6-line caller instead of ~20 lines.

### Playwright Workers

Change `frontend/playwright.config.ts`:

```typescript
workers: process.env.CI ? 4 : undefined,
```

With 4 workers, the 4 browser projects run concurrently instead of sequentially.

### Files Changed

| File | Change |
|------|--------|
| `.github/workflows/e2e-suite.yml` | New reusable workflow |
| `.github/workflows/e2e.yml` | Refactor 8 jobs to use reusable workflow |
| `frontend/playwright.config.ts` | CI workers: 1 → 4 |

### Risks

- Tests sharing mutable state could flake with parallel workers (mitigated: E2E tests hit staging API, should be independent)
- Reusable workflows have a limitation: caller and callee must be in the same repo (satisfied: both in `.github/workflows/`)
