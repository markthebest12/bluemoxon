# E2E Testing Design: Holistic BMX Coverage

## Decisions

| Decision | Choice |
|----------|--------|
| Auth strategy | Service account + Playwright storageState |
| MFA handling | MFA-exempt test accounts (no TOTP) |
| Role testing | 3 separate Cognito users (admin, editor, viewer) |
| Passwords | Hardened, AWS Secrets Manager, never displayed |
| CI strategy | Both: GitHub Actions pipeline + Claude skill |
| CI triggers | Suite-level path-based triggers + always-on smoke |
| Suite structure | 8 suites, P0-P3 priority |

## Architecture

### Auth Setup

```
globalSetup.ts
├── Fetch passwords from AWS Secrets Manager
│   ├── bluemoxon-staging/e2e-admin-password
│   ├── bluemoxon-staging/e2e-editor-password
│   └── bluemoxon-staging/e2e-viewer-password
├── Headless Cognito login (3 users, no MFA)
│   ├── e2e-test-admin@bluemoxon.com → .auth/admin.json
│   ├── e2e-test-editor@bluemoxon.com → .auth/editor.json
│   └── e2e-test-viewer@bluemoxon.com → .auth/viewer.json
└── storageState files cached for all test projects
```

### Cognito Users

| User | Role | MFA | Purpose |
|------|------|-----|---------|
| e2e-test-admin@bluemoxon.com | admin | exempt | Admin page tests, full access flows |
| e2e-test-editor@bluemoxon.com | editor | exempt | Book CRUD, entity management |
| e2e-test-viewer@bluemoxon.com | viewer | exempt | Read-only flows, social circles, dashboard |

All passwords stored in AWS Secrets Manager. CI accesses via IAM role. Local dev via `AWS_PROFILE=bmx-staging`.

### Test Suite Map

| Suite | Files | Trigger Paths | Role(s) | Priority |
|-------|-------|--------------|---------|----------|
| smoke | `e2e/smoke.spec.ts` | any `frontend/src/**` | all 3 | P0 |
| auth | `e2e/auth.spec.ts` | `auth.*`, `router.*`, `LoginView.*` | all 3 | P1 |
| books | `e2e/books.spec.ts` (existing + CRUD) | `views/Books*`, `components/book-detail/**` | editor, viewer | P1 |
| social-circles | `e2e/socialcircles-*.spec.ts` (existing, route-fixed) | `components/socialcircles/**`, `views/SocialCircles*` | viewer | P2 |
| dashboard | `e2e/home.spec.ts` (existing) | `views/Home*`, `components/dashboard/**` | viewer | P2 |
| admin | `e2e/admin.spec.ts` | `views/Admin*`, `components/admin/**` | admin | P3 |
| profile | `e2e/profile.spec.ts` | `views/Profile*` | viewer | P3 |
| performance | `e2e/performance.spec.ts` (existing) | any `frontend/src/**` | viewer | P3 (optional) |

### Smoke Suite Coverage

Lightweight route-loading test per role (~15s total):

```typescript
const routes = ['/', '/books', '/social-circles', '/profile', '/reports/insurance'];
const adminRoutes = ['/admin', '/admin/acquisitions', '/admin/config'];

// viewer: all routes load, admin routes redirect
// editor: all routes load, admin routes redirect (except /admin/config)
// admin: all routes load including admin
```

### CI Pipeline

```yaml
# .github/workflows/e2e.yml
name: E2E Tests
on:
  pull_request:
    branches: [staging]
    paths: [frontend/src/**, frontend/e2e/**]

jobs:
  smoke:
    # Always runs on any frontend change
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npx playwright install chromium
      - run: npx playwright test e2e/smoke.spec.ts
    env:
      BASE_URL: https://staging.app.bluemoxon.com

  social-circles:
    # Only when social-circles code changes
    if: contains(needs.changes.outputs.paths, 'socialcircles')
    runs-on: ubuntu-latest
    steps:
      - run: npx playwright test e2e/socialcircles-*.spec.ts

  books:
    if: contains(needs.changes.outputs.paths, 'book')
    # ...

  auth:
    if: contains(needs.changes.outputs.paths, 'auth')
    # ...

  # etc. per suite
```

Path detection via `dorny/paths-filter` action or similar.

### Secrets Flow

```
AWS Secrets Manager
└── bluemoxon-staging/e2e-*-password
    ├── CI: GitHub Actions → OIDC → IAM role → SecretsManager
    └── Local: AWS_PROFILE=bmx-staging → SecretsManager
```

globalSetup.ts fetches at runtime:

```typescript
import { SecretsManagerClient, GetSecretValueCommand } from '@aws-sdk/client-secrets-manager';

async function getPassword(secretId: string): Promise<string> {
  const client = new SecretsManagerClient({ region: 'us-east-1' });
  const response = await client.send(new GetSecretValueCommand({ SecretId: secretId }));
  return response.SecretString!;
}
```

### Playwright Config Changes

```typescript
// playwright.config.ts updates
{
  globalSetup: './e2e/global-setup.ts',
  use: {
    baseURL: process.env.BASE_URL || 'https://staging.app.bluemoxon.com',
    // default to viewer
    storageState: '.auth/viewer.json',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'Mobile Chrome', use: { ...devices['Pixel 5'] } },
    { name: 'Mobile Safari', use: { ...devices['iPhone 12'] } },
    // Firefox dropped - Chromium + WebKit covers real engine differences
  ]
}
```

### bmx-e2e-validation Skill Update

Skill evolves from MCP-browser manual validation to:

```bash
# Headless, non-interactive
BASE_URL=https://app.bluemoxon.com npx playwright test --project=chromium
```

Skill retained for:
- Post-deploy production validation
- Ad-hoc full-suite runs
- Debugging specific failures with `--headed` flag

## Implementation Order

### Phase 1: Foundation (Issues #1519, #1520)
1. Fix route mismatch: `/socialcircles` → `/social-circles` in 4 E2E files
2. Fix Playwright config baseURL default: `bluemoxon.com` → `staging.app.bluemoxon.com`
3. Create 3 Cognito users (mfa_exempt) + store passwords in Secrets Manager
4. Implement `global-setup.ts` with Cognito login + storageState
5. Verify existing tests pass with auth

### Phase 2: Smoke + Auth Suites
6. Create `smoke.spec.ts` - all routes, all roles
7. Create `auth.spec.ts` - login, logout, role guards, redirect behavior
8. Extend `books.spec.ts` - add CRUD tests (create, edit) for editor role

### Phase 3: CI Pipeline
9. Create `.github/workflows/e2e.yml` with path-based triggers
10. Configure GitHub OIDC → IAM role for Secrets Manager access
11. Update `bmx-e2e-validation` skill for headless execution

### Phase 4: Remaining Suites
12. Create `admin.spec.ts` - admin dashboard, acquisitions
13. Create `profile.spec.ts` - profile editing
14. Add role-guard tests across suites (viewer can't access admin, etc.)

## Resolved Questions

| Question | Decision |
|----------|----------|
| Browser projects | Drop Firefox only. Keep Chromium, WebKit (Safari), Mobile Chrome, Mobile Safari (4 projects) |
| Performance suite in CI | CI with relaxed budgets (2x thresholds). Catches catastrophic regressions without false positives from runner variance. Tight budgets for local/skill runs. |
| Production E2E post-deploy | Automated smoke post-deploy (in deploy workflow, ~15s). Full suite via `bmx-e2e-validation` skill on demand. |
