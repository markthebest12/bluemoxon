# E2E Testing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement holistic, authenticated E2E testing across all BMX flows with CI pipeline integration and Claude skill support.

**Architecture:** Three MFA-exempt Cognito service accounts (admin/editor/viewer) authenticate via Playwright globalSetup, storing JWT tokens in storageState files. Tests run against staging in CI with path-based suite triggers. A Claude skill provides on-demand production validation.

**Tech Stack:** Playwright 1.57+, AWS Amplify (Cognito auth), AWS SDK (Secrets Manager), GitHub Actions (OIDC), dorny/paths-filter

**Design Doc:** `docs/plans/2026-01-29-e2e-testing-design.md`

---

## Phase 1: Foundation

### Task 1: Fix E2E route mismatch (#1520)

**Files:**
- Modify: `frontend/e2e/socialcircles-layout.spec.ts:14`
- Modify: `frontend/e2e/socialcircles-search.spec.ts:16`
- Modify: `frontend/e2e/socialcircles-path.spec.ts:16`
- Modify: `frontend/e2e/socialcircles-stats.spec.ts:41`

**Step 1: Fix all 4 files**

In each file, replace:
```typescript
await page.goto("/socialcircles");
```
with:
```typescript
await page.goto("/social-circles");
```

**Step 2: Verify no other references**

Run: `grep -r "socialcircles" frontend/e2e/ --include="*.ts"`
Expected: No matches (file names use `socialcircles` which is fine - only the route path matters)

**Step 3: Commit**

```
fix(e2e): correct Social Circles route path

Change /socialcircles to /social-circles in all 4 E2E test files
to match the actual Vue Router path definition.

Closes #1520
```

---

### Task 2: Fix Playwright config baseURL and browser projects

**Files:**
- Modify: `frontend/playwright.config.ts`
- Modify: `frontend/.gitignore`

**Step 1: Update playwright.config.ts**

Replace the entire config with:
```typescript
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  globalSetup: "./e2e/global-setup.ts",
  use: {
    baseURL: process.env.BASE_URL || "https://staging.app.bluemoxon.com",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    storageState: ".auth/viewer.json",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
    {
      name: "Mobile Chrome",
      use: { ...devices["Pixel 5"] },
    },
    {
      name: "Mobile Safari",
      use: { ...devices["iPhone 12"] },
    },
  ],
});
```

Key changes:
- `globalSetup` added (points to file created in Task 4)
- `baseURL` default changed from `bluemoxon.com` to `staging.app.bluemoxon.com`
- `storageState` defaults to viewer role
- Firefox project removed

**Step 2: Add `.auth/` to .gitignore**

Append to `frontend/.gitignore`:
```
# E2E auth state (contains JWT tokens)
.auth/
```

**Step 3: Commit**

```
feat(e2e): update Playwright config for authenticated testing

- Default baseURL to staging.app.bluemoxon.com (was bluemoxon.com)
- Add globalSetup for Cognito auth
- Default storageState to viewer role
- Drop Firefox, keep Chromium + WebKit + mobile
- Gitignore .auth/ directory (contains JWT tokens)
```

---

### Task 3: Create Cognito test users and store passwords

**This is a manual/infrastructure task - not code.**

**Step 1: Generate 3 hardened passwords**

Use a password manager or `openssl rand -base64 32` to generate three passwords meeting Cognito policy (12+ chars, upper, lower, number, symbol). Never display them on screen.

**Step 2: Create 3 Cognito users in staging**

```bash
AWS_PROFILE=bmx-staging aws cognito-idp admin-create-user \
  --user-pool-id us-west-2_mV1xeyw7v \
  --username "e2e-test-admin@bluemoxon.com" \
  --user-attributes Name=email,Value=e2e-test-admin@bluemoxon.com Name=email_verified,Value=true \
  --message-action SUPPRESS \
  --region us-west-2
```

Repeat for `e2e-test-editor@bluemoxon.com` and `e2e-test-viewer@bluemoxon.com`.

**Step 3: Set permanent passwords**

```bash
AWS_PROFILE=bmx-staging aws cognito-idp admin-set-user-password \
  --user-pool-id us-west-2_mV1xeyw7v \
  --username "e2e-test-admin@bluemoxon.com" \
  --password "THE_GENERATED_PASSWORD" \
  --permanent \
  --region us-west-2
```

Repeat for editor and viewer.

**Step 4: Store passwords in Secrets Manager**

```bash
AWS_PROFILE=bmx-staging aws secretsmanager create-secret \
  --name "bluemoxon-staging/e2e-admin-password" \
  --secret-string "THE_GENERATED_PASSWORD" \
  --region us-west-2
```

Repeat for `e2e-editor-password` and `e2e-viewer-password`.

**Step 5: Create user profiles in the database**

Use the BMX API to ensure each user has the correct role and mfa_exempt flag:

```bash
bmx-api POST /admin/users '{"email":"e2e-test-admin@bluemoxon.com","role":"admin","mfa_exempt":true}'
bmx-api POST /admin/users '{"email":"e2e-test-editor@bluemoxon.com","role":"editor","mfa_exempt":true}'
bmx-api POST /admin/users '{"email":"e2e-test-viewer@bluemoxon.com","role":"viewer","mfa_exempt":true}'
```

(Exact API shape may vary - check `/admin/users` endpoint. May need to create users via Cognito trigger or direct DB insert instead.)

**Step 6: Verify login works**

Test one user manually:
```bash
# This is just to verify - use AWS CLI
AWS_PROFILE=bmx-staging aws cognito-idp admin-initiate-auth \
  --user-pool-id us-west-2_mV1xeyw7v \
  --client-id 4bb77j6uskmjibq27i15ajfpqq \
  --auth-flow ADMIN_USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=e2e-test-viewer@bluemoxon.com,PASSWORD=REDACTED \
  --region us-west-2
```

Expected: Returns `AuthenticationResult` with `AccessToken`, `IdToken`, `RefreshToken` (no MFA challenge).

---

### Task 4: Implement global-setup.ts

**Files:**
- Create: `frontend/e2e/global-setup.ts`
- Modify: `frontend/package.json` (add `@aws-sdk/client-secrets-manager` dependency)

**Step 1: Install AWS SDK dependency**

Run: `npm install --save-dev @aws-sdk/client-secrets-manager --prefix frontend`

**Step 2: Create global-setup.ts**

Create `frontend/e2e/global-setup.ts`:

```typescript
import { chromium, type FullConfig } from "@playwright/test";
import { SecretsManagerClient, GetSecretValueCommand } from "@aws-sdk/client-secrets-manager";

const COGNITO_USER_POOL_ID = "us-west-2_mV1xeyw7v";
const COGNITO_CLIENT_ID = "4bb77j6uskmjibq27i15ajfpqq";
const COGNITO_DOMAIN = "bluemoxon-staging.auth.us-west-2.amazoncognito.com";

interface TestUser {
  email: string;
  secretId: string;
  storageStatePath: string;
}

const TEST_USERS: TestUser[] = [
  {
    email: "e2e-test-admin@bluemoxon.com",
    secretId: "bluemoxon-staging/e2e-admin-password",
    storageStatePath: ".auth/admin.json",
  },
  {
    email: "e2e-test-editor@bluemoxon.com",
    secretId: "bluemoxon-staging/e2e-editor-password",
    storageStatePath: ".auth/editor.json",
  },
  {
    email: "e2e-test-viewer@bluemoxon.com",
    secretId: "bluemoxon-staging/e2e-viewer-password",
    storageStatePath: ".auth/viewer.json",
  },
];

async function getPassword(secretId: string): Promise<string> {
  const client = new SecretsManagerClient({ region: "us-west-2" });
  const response = await client.send(
    new GetSecretValueCommand({ SecretId: secretId })
  );
  if (!response.SecretString) {
    throw new Error(`Secret ${secretId} has no string value`);
  }
  return response.SecretString;
}

async function authenticateUser(
  user: TestUser,
  baseURL: string
): Promise<void> {
  const password = await getPassword(user.secretId);
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  // Navigate to the app - will redirect to Cognito login
  await page.goto(baseURL);

  // Wait for Cognito hosted UI or app login page
  // The app uses Amplify signIn, so we interact with the app's login form
  await page.waitForSelector('[data-testid="login-form"], input[name="username"]', {
    timeout: 15000,
  });

  // Fill login form
  // Check if we're on app login page or Cognito hosted UI
  const appLoginForm = await page.$('[data-testid="login-form"]');
  if (appLoginForm) {
    // App's own login form
    await page.fill('[data-testid="username-input"], input[type="email"]', user.email);
    await page.fill('[data-testid="password-input"], input[type="password"]', password);
    await page.click('[data-testid="login-button"], button[type="submit"]');
  } else {
    // Cognito hosted UI
    await page.fill('input[name="username"]', user.email);
    await page.fill('input[name="password"]', password);
    await page.click('input[name="signInSubmitButton"], button[type="submit"]');
  }

  // Wait for auth to complete - app should redirect to home
  await page.waitForURL("**/", { timeout: 30000 });

  // Verify authenticated - wait for app content to load
  await page.waitForSelector('[data-testid="nav-bar"], nav', { timeout: 15000 });

  // Save storage state (cookies + localStorage with JWT tokens)
  await context.storageState({ path: user.storageStatePath });

  await browser.close();
}

async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0]?.use?.baseURL || "https://staging.app.bluemoxon.com";

  console.log(`[E2E Setup] Authenticating 3 test users against ${baseURL}...`);

  // Authenticate all 3 users in parallel
  await Promise.all(
    TEST_USERS.map(async (user) => {
      try {
        await authenticateUser(user, baseURL);
        console.log(`[E2E Setup] Authenticated ${user.email}`);
      } catch (error) {
        console.error(`[E2E Setup] Failed to authenticate ${user.email}:`, error);
        throw error;
      }
    })
  );

  console.log("[E2E Setup] All users authenticated. storageState files saved.");
}

export default globalSetup;
```

**Important notes for implementer:**
- The login form selectors above are best guesses. Read `frontend/src/views/LoginView.vue` to get the actual `data-testid` attributes or form structure. Adjust selectors accordingly.
- The Cognito hosted UI vs app login form branching may not be needed if the app always uses its own form. Check the actual login flow.
- If the app uses Amplify's `signIn()` SDK call (not hosted UI redirect), the browser-based login approach above may not work. In that case, use the Cognito `AdminInitiateAuth` API directly instead of browser login. See Task 4 Alternative below.

**Step 3: Verify globalSetup runs**

Run: `cd frontend; npx playwright test --project=chromium e2e/home.spec.ts`

Expected: globalSetup authenticates all 3 users, home.spec.ts runs authenticated.

**Step 4: Commit**

```
feat(e2e): add Cognito auth globalSetup with storageState

- globalSetup authenticates 3 service accounts (admin/editor/viewer)
- Fetches passwords from AWS Secrets Manager
- Saves storageState to .auth/*.json for test reuse
- All tests run authenticated by default (viewer role)

Closes #1519
```

---

### Task 4 Alternative: SDK-based auth (if browser login doesn't work)

If the app uses Amplify `signIn()` rather than Cognito hosted UI redirect, the browser-based approach in Task 4 won't work. Use the Cognito `AdminInitiateAuth` API instead:

**Replace the `authenticateUser` function with:**

```typescript
import { CognitoIdentityProviderClient, AdminInitiateAuthCommand } from "@aws-sdk/client-cognito-identity-provider";

async function authenticateUser(
  user: TestUser,
  baseURL: string
): Promise<void> {
  const password = await getPassword(user.secretId);

  // Use AdminInitiateAuth to get tokens without browser
  const cognitoClient = new CognitoIdentityProviderClient({ region: "us-west-2" });
  const authResult = await cognitoClient.send(
    new AdminInitiateAuthCommand({
      UserPoolId: COGNITO_USER_POOL_ID,
      ClientId: COGNITO_CLIENT_ID,
      AuthFlow: "ADMIN_USER_PASSWORD_AUTH",
      AuthParameters: {
        USERNAME: user.email,
        PASSWORD: password,
      },
    })
  );

  if (!authResult.AuthenticationResult) {
    throw new Error(`Auth failed for ${user.email}: no AuthenticationResult`);
  }

  const { IdToken, AccessToken, RefreshToken } = authResult.AuthenticationResult;

  // Build storageState that Amplify expects
  // Amplify stores tokens in localStorage with specific key patterns
  const amplifyKeyPrefix = `CognitoIdentityServiceProvider.${COGNITO_CLIENT_ID}`;
  const userKey = user.email;

  const localStorage = [
    { name: `${amplifyKeyPrefix}.${userKey}.idToken`, value: IdToken! },
    { name: `${amplifyKeyPrefix}.${userKey}.accessToken`, value: AccessToken! },
    { name: `${amplifyKeyPrefix}.${userKey}.refreshToken`, value: RefreshToken! },
    { name: `${amplifyKeyPrefix}.LastAuthUser`, value: userKey },
  ];

  // Write storageState file
  const storageState = {
    cookies: [],
    origins: [
      {
        origin: baseURL,
        localStorage: localStorage,
      },
    ],
  };

  const fs = await import("fs");
  const path = await import("path");

  // Ensure .auth directory exists
  const authDir = path.dirname(user.storageStatePath);
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
  }

  fs.writeFileSync(user.storageStatePath, JSON.stringify(storageState, null, 2));
}
```

**Additional dependency needed:**
Run: `npm install --save-dev @aws-sdk/client-cognito-identity-provider --prefix frontend`

**Important:** The localStorage key format depends on which version of Amplify is used (v5 vs v6). Check `frontend/node_modules/aws-amplify/` to confirm the version. Amplify v6 may use different storage key patterns. Read the actual localStorage in a browser DevTools session to see the exact keys.

---

### Task 5: Verify existing tests pass with auth

**Step 1: Run social circles tests**

Run: `cd frontend; npx playwright test --project=chromium e2e/socialcircles-layout.spec.ts`

Expected: Tests pass (route fixed, auth provided via storageState).

**Step 2: Run all existing tests**

Run: `cd frontend; npx playwright test --project=chromium`

Expected: All existing tests pass. If any fail, debug and fix before proceeding.

**Step 3: Commit (if any fixes needed)**

```
fix(e2e): adjust tests for authenticated storageState
```

---

## Phase 2: Smoke + Auth Suites

### Task 6: Create smoke test suite

**Files:**
- Create: `frontend/e2e/smoke.spec.ts`

**Step 1: Create smoke.spec.ts**

```typescript
import { test, expect } from "@playwright/test";

/**
 * Smoke tests - verify every route loads for each role.
 * Runs on every frontend change (P0 priority).
 */

const viewerRoutes = [
  { path: "/", name: "Dashboard" },
  { path: "/books", name: "Books" },
  { path: "/social-circles", name: "Social Circles" },
  { path: "/profile", name: "Profile" },
  { path: "/reports/insurance", name: "Insurance Report" },
];

const adminRoutes = [
  { path: "/admin", name: "Admin" },
  { path: "/admin/acquisitions", name: "Acquisitions" },
];

const editorRoutes = [
  { path: "/admin/config", name: "Admin Config" },
];

test.describe("Smoke: Viewer routes", () => {
  test.use({ storageState: ".auth/viewer.json" });

  for (const route of viewerRoutes) {
    test(`${route.name} (${route.path}) loads`, async ({ page }) => {
      await page.goto(route.path);
      // Should not redirect to login
      await expect(page).not.toHaveURL(/\/login/);
      // Page should have content (not blank)
      await expect(page.locator("body")).not.toBeEmpty();
    });
  }

  for (const route of adminRoutes) {
    test(`viewer redirected from ${route.name} (${route.path})`, async ({ page }) => {
      await page.goto(route.path);
      // Viewer should be redirected to home, not admin
      await expect(page).toHaveURL("/");
    });
  }
});

test.describe("Smoke: Editor routes", () => {
  test.use({ storageState: ".auth/editor.json" });

  for (const route of viewerRoutes) {
    test(`${route.name} (${route.path}) loads`, async ({ page }) => {
      await page.goto(route.path);
      await expect(page).not.toHaveURL(/\/login/);
      await expect(page.locator("body")).not.toBeEmpty();
    });
  }

  test("editor can access admin config", async ({ page }) => {
    await page.goto("/admin/config");
    await expect(page).not.toHaveURL(/\/login/);
  });
});

test.describe("Smoke: Admin routes", () => {
  test.use({ storageState: ".auth/admin.json" });

  const allRoutes = [...viewerRoutes, ...adminRoutes, ...editorRoutes];

  for (const route of allRoutes) {
    test(`${route.name} (${route.path}) loads`, async ({ page }) => {
      await page.goto(route.path);
      await expect(page).not.toHaveURL(/\/login/);
      await expect(page.locator("body")).not.toBeEmpty();
    });
  }
});
```

**Step 2: Run smoke tests**

Run: `cd frontend; npx playwright test --project=chromium e2e/smoke.spec.ts`

Expected: All routes load for appropriate roles, role guards redirect correctly.

**Step 3: Commit**

```
feat(e2e): add smoke test suite for all routes and roles

Tests every route loads for viewer/editor/admin roles.
Verifies role guards redirect unauthorized users.
P0 priority - runs on every frontend change.
```

---

### Task 7: Create auth test suite

**Files:**
- Create: `frontend/e2e/auth.spec.ts`

**Step 1: Read LoginView.vue to understand login form structure**

Read: `frontend/src/views/LoginView.vue`
Note the exact `data-testid` attributes and form elements.

**Step 2: Create auth.spec.ts**

```typescript
import { test, expect } from "@playwright/test";

/**
 * Auth tests - login, logout, session, role guards.
 * P1 priority - runs when auth/router code changes.
 */

test.describe("Authentication", () => {
  test.describe("Unauthenticated access", () => {
    // Use empty storage state (no auth)
    test.use({ storageState: { cookies: [], origins: [] } });

    test("protected routes redirect to login", async ({ page }) => {
      await page.goto("/books");
      await expect(page).toHaveURL(/\/login/);
    });

    test("login page loads", async ({ page }) => {
      await page.goto("/login");
      // Should see login form
      await expect(page.locator("form, [data-testid='login-form']")).toBeVisible();
    });
  });

  test.describe("Role guards", () => {
    test("viewer cannot access admin", async ({ page }) => {
      // Default storageState is viewer
      await page.goto("/admin");
      await expect(page).toHaveURL("/");
    });

    test("viewer cannot access admin config", async ({ page }) => {
      await page.goto("/admin/config");
      await expect(page).toHaveURL("/");
    });

    test("viewer cannot access acquisitions", async ({ page }) => {
      await page.goto("/admin/acquisitions");
      await expect(page).toHaveURL("/");
    });
  });

  test.describe("Editor role guards", () => {
    test.use({ storageState: ".auth/editor.json" });

    test("editor can access admin config", async ({ page }) => {
      await page.goto("/admin/config");
      await expect(page).not.toHaveURL("/");
    });

    test("editor cannot access admin dashboard", async ({ page }) => {
      await page.goto("/admin");
      await expect(page).toHaveURL("/");
    });
  });

  test.describe("Admin access", () => {
    test.use({ storageState: ".auth/admin.json" });

    test("admin can access all admin routes", async ({ page }) => {
      await page.goto("/admin");
      await expect(page).not.toHaveURL(/\/login/);
      await expect(page).not.toHaveURL("/");
      // Verify admin content visible (adjust selector based on actual page)
      await expect(page.locator("main, [data-testid='admin-view']")).toBeVisible();
    });

    test("admin can access acquisitions", async ({ page }) => {
      await page.goto("/admin/acquisitions");
      await expect(page).not.toHaveURL(/\/login/);
    });
  });
});
```

**Step 3: Run auth tests**

Run: `cd frontend; npx playwright test --project=chromium e2e/auth.spec.ts`

Expected: All pass.

**Step 4: Commit**

```
feat(e2e): add auth test suite for login and role guards

Tests unauthenticated redirect, viewer/editor/admin role guards.
P1 priority - runs when auth or router code changes.
```

---

### Task 8: Extend books test suite with CRUD

**Files:**
- Modify: `frontend/e2e/books.spec.ts`

**Step 1: Read existing books.spec.ts and BookCreateView.vue**

Read: `frontend/e2e/books.spec.ts`
Read: `frontend/src/views/BookCreateView.vue`
Read: `frontend/src/views/BookEditView.vue`

Note the form fields, data-testid attributes, and validation.

**Step 2: Add editor CRUD tests to books.spec.ts**

Append a new describe block to the existing file:

```typescript
test.describe("Book CRUD (editor)", () => {
  test.use({ storageState: ".auth/editor.json" });

  test("can navigate to create book form", async ({ page }) => {
    await page.goto("/books/new");
    await expect(page).not.toHaveURL(/\/login/);
    // Should see the create form
    await expect(page.locator("form, [data-testid='book-form']")).toBeVisible();
  });

  test("create form has required fields", async ({ page }) => {
    await page.goto("/books/new");
    // Check for title field at minimum
    await expect(page.locator("[data-testid='title-input'], input[name='title']")).toBeVisible();
  });

  // Note: Actual create/edit/delete tests should be carefully designed
  // to not pollute production data. Consider:
  // - Create with unique prefix "E2E-TEST-" for easy identification
  // - Clean up created books in afterAll
  // - Or use a dedicated test book ID for edit tests
});
```

**Important note for implementer:** Book CRUD tests that create/modify data need a cleanup strategy. Either:
1. Use a known test book that already exists (for edit tests)
2. Create books with a prefix like "E2E-TEST-" and clean up in afterAll
3. Only test navigation to forms and field visibility (no actual data mutations)

Choose based on how acceptable test data in staging is. For now, test form visibility only. Add mutation tests later with proper cleanup.

**Step 3: Run books tests**

Run: `cd frontend; npx playwright test --project=chromium e2e/books.spec.ts`

**Step 4: Commit**

```
feat(e2e): add book CRUD navigation tests for editor role

Tests editor can access create/edit forms.
Form field visibility verified without data mutation.
```

---

## Phase 3: CI Pipeline

### Task 9: Create E2E GitHub Actions workflow

**Files:**
- Create: `.github/workflows/e2e.yml`

**Step 1: Read existing ci.yml for patterns**

Read: `.github/workflows/ci.yml` (first 50 lines for the structure, permissions, env setup)

**Step 2: Create e2e.yml**

```yaml
name: E2E Tests

on:
  pull_request:
    branches: [staging, main]
    paths:
      - "frontend/src/**"
      - "frontend/e2e/**"
      - "frontend/playwright.config.ts"

permissions:
  id-token: write
  contents: read

env:
  BASE_URL: https://staging.app.bluemoxon.com

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      socialcircles: ${{ steps.filter.outputs.socialcircles }}
      books: ${{ steps.filter.outputs.books }}
      auth: ${{ steps.filter.outputs.auth }}
      dashboard: ${{ steps.filter.outputs.dashboard }}
      admin: ${{ steps.filter.outputs.admin }}
      profile: ${{ steps.filter.outputs.profile }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            socialcircles:
              - 'frontend/src/components/socialcircles/**'
              - 'frontend/src/views/SocialCirclesView.vue'
              - 'frontend/e2e/socialcircles-*.spec.ts'
            books:
              - 'frontend/src/views/Books*.vue'
              - 'frontend/src/views/BookCreate*.vue'
              - 'frontend/src/views/BookEdit*.vue'
              - 'frontend/src/views/BookDetail*.vue'
              - 'frontend/src/components/book-detail/**'
              - 'frontend/src/components/books/**'
              - 'frontend/e2e/books.spec.ts'
            auth:
              - 'frontend/src/stores/auth.*'
              - 'frontend/src/router/**'
              - 'frontend/src/views/LoginView.vue'
              - 'frontend/e2e/auth.spec.ts'
            dashboard:
              - 'frontend/src/views/HomeView.vue'
              - 'frontend/src/components/dashboard/**'
              - 'frontend/e2e/home.spec.ts'
            admin:
              - 'frontend/src/views/Admin*.vue'
              - 'frontend/src/components/admin/**'
              - 'frontend/e2e/admin.spec.ts'
            profile:
              - 'frontend/src/views/ProfileView.vue'
              - 'frontend/e2e/profile.spec.ts'

  smoke:
    needs: detect-changes
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: cd frontend && npm ci

      - name: Install Playwright browsers
        run: cd frontend && npx playwright install --with-deps chromium webkit

      - name: Configure AWS credentials via OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_STAGING_ROLE_ARN }}
          aws-region: us-west-2

      - name: Run smoke tests
        run: cd frontend && npx playwright test e2e/smoke.spec.ts
        env:
          BASE_URL: ${{ env.BASE_URL }}

      - name: Upload test results
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: smoke-test-results
          path: |
            frontend/test-results/
            frontend/playwright-report/

  social-circles:
    needs: detect-changes
    if: needs.detect-changes.outputs.socialcircles == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - run: cd frontend && npm ci
      - run: cd frontend && npx playwright install --with-deps chromium webkit
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_STAGING_ROLE_ARN }}
          aws-region: us-west-2
      - name: Run social circles tests
        run: cd frontend && npx playwright test e2e/socialcircles-*.spec.ts
      - if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: social-circles-test-results
          path: frontend/test-results/

  books:
    needs: detect-changes
    if: needs.detect-changes.outputs.books == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - run: cd frontend && npm ci
      - run: cd frontend && npx playwright install --with-deps chromium webkit
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_STAGING_ROLE_ARN }}
          aws-region: us-west-2
      - name: Run books tests
        run: cd frontend && npx playwright test e2e/books.spec.ts
      - if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: books-test-results
          path: frontend/test-results/

  auth:
    needs: detect-changes
    if: needs.detect-changes.outputs.auth == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - run: cd frontend && npm ci
      - run: cd frontend && npx playwright install --with-deps chromium webkit
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_STAGING_ROLE_ARN }}
          aws-region: us-west-2
      - name: Run auth tests
        run: cd frontend && npx playwright test e2e/auth.spec.ts
      - if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: auth-test-results
          path: frontend/test-results/

  dashboard:
    needs: detect-changes
    if: needs.detect-changes.outputs.dashboard == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - run: cd frontend && npm ci
      - run: cd frontend && npx playwright install --with-deps chromium webkit
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_STAGING_ROLE_ARN }}
          aws-region: us-west-2
      - name: Run dashboard tests
        run: cd frontend && npx playwright test e2e/home.spec.ts
      - if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: dashboard-test-results
          path: frontend/test-results/

  performance:
    needs: detect-changes
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - run: cd frontend && npm ci
      - run: cd frontend && npx playwright install --with-deps chromium
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_STAGING_ROLE_ARN }}
          aws-region: us-west-2
      - name: Run performance tests (relaxed budgets)
        run: cd frontend && E2E_RELAXED_BUDGETS=true npx playwright test e2e/performance.spec.ts --project=chromium
      - if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: performance-test-results
          path: frontend/test-results/
```

**Step 3: Commit**

```
feat(ci): add E2E test workflow with path-based triggers

- Smoke suite runs on any frontend change
- Suite-specific jobs trigger only when relevant paths change
- Uses dorny/paths-filter for path detection
- AWS OIDC for Secrets Manager access
- Artifact upload on failure for debugging
```

---

### Task 10: Add post-deploy smoke to deploy workflow

**Files:**
- Modify: `.github/workflows/deploy.yml`

**Step 1: Read deploy.yml to find where to add post-deploy step**

Read the deploy workflow to find the deployment completion point. Add an E2E smoke job after successful frontend deployment.

**Step 2: Add post-deploy smoke job**

Add after the existing smoke test / health check job:

```yaml
  e2e-smoke:
    needs: [deploy-frontend]
    if: success()
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - run: cd frontend && npm ci
      - run: cd frontend && npx playwright install --with-deps chromium
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_STAGING_ROLE_ARN }}
          aws-region: us-west-2
      - name: E2E smoke test
        run: cd frontend && npx playwright test e2e/smoke.spec.ts --project=chromium
        env:
          BASE_URL: ${{ needs.configure.outputs.app_url }}
```

**Important:** The exact job name to depend on (`deploy-frontend`) and the app URL output variable need to match the existing workflow structure. Adjust based on what you find in deploy.yml.

**Step 3: Commit**

```
feat(ci): add post-deploy E2E smoke test

Runs smoke suite after frontend deployment to verify
routes load correctly with auth in the deployed environment.
```

---

### Task 11: Update performance tests for relaxed CI budgets

**Files:**
- Modify: `frontend/e2e/performance.spec.ts`

**Step 1: Add environment-aware budgets**

At the top of performance.spec.ts, after the existing helpers, add:

```typescript
// Relaxed budgets for CI (runner performance varies)
const RELAXED = !!process.env.E2E_RELAXED_BUDGETS;
const FCP_BUDGET = RELAXED ? 5000 : 2500;
const DCL_BUDGET = RELAXED ? 6000 : 3000;
const BOOKS_FCP_BUDGET = RELAXED ? 6000 : 3000;
```

Then replace the hardcoded assertion values:
- `expect(metrics.firstContentfulPaint).toBeLessThan(2500)` → `toBeLessThan(FCP_BUDGET)`
- `expect(metrics.domContentLoaded).toBeLessThan(3000)` → `toBeLessThan(DCL_BUDGET)`
- `expect(metrics.firstContentfulPaint).toBeLessThan(3000)` (books) → `toBeLessThan(BOOKS_FCP_BUDGET)`

**Step 2: Commit**

```
feat(e2e): add relaxed performance budgets for CI

CI runners have variable performance. E2E_RELAXED_BUDGETS=true
doubles thresholds to catch catastrophic regressions without
false positives. Local runs keep tight budgets.
```

---

### Task 12: Update bmx-e2e-validation skill

**Files:**
- Modify: `~/.claude/skills/bmx-e2e-validation/SKILL.md`

**Step 1: Rewrite skill for headless execution**

Replace the existing skill content with updated version that:
- Defaults to headless `npx playwright test` execution
- Falls back to MCP browser for debugging
- Supports staging and production targets
- References the storageState auth setup

**Step 2: Commit (skill files not in repo, skip)**

---

## Phase 4: Remaining Suites

### Task 13: Create admin test suite

**Files:**
- Create: `frontend/e2e/admin.spec.ts`

**Step 1: Read admin views**

Read: `frontend/src/views/AdminView.vue`
Read: `frontend/src/views/AcquisitionsView.vue`
Read: `frontend/src/views/AdminConfigView.vue`

**Step 2: Create admin.spec.ts**

```typescript
import { test, expect } from "@playwright/test";

test.describe("Admin Dashboard", () => {
  test.use({ storageState: ".auth/admin.json" });

  test("admin dashboard loads", async ({ page }) => {
    await page.goto("/admin");
    await expect(page.locator("main")).toBeVisible();
    // Verify admin-specific content (adjust selectors)
  });

  test("acquisitions page loads with table", async ({ page }) => {
    await page.goto("/admin/acquisitions");
    // Should have a table or list of acquisitions
    await expect(page.locator("table, [data-testid='acquisitions-list']")).toBeVisible();
  });

  test("admin config page loads", async ({ page }) => {
    await page.goto("/admin/config");
    await expect(page.locator("main")).toBeVisible();
  });
});
```

**Note:** Selectors are placeholders. Implementer must read the actual view components to determine correct selectors.

**Step 3: Commit**

```
feat(e2e): add admin test suite

Tests admin dashboard, acquisitions, and config pages.
P3 priority - runs when admin code changes.
```

---

### Task 14: Create profile test suite

**Files:**
- Create: `frontend/e2e/profile.spec.ts`

**Step 1: Read ProfileView.vue**

Read: `frontend/src/views/ProfileView.vue`

**Step 2: Create profile.spec.ts**

```typescript
import { test, expect } from "@playwright/test";

test.describe("Profile", () => {
  test.use({ storageState: ".auth/viewer.json" });

  test("profile page loads", async ({ page }) => {
    await page.goto("/profile");
    await expect(page).not.toHaveURL(/\/login/);
    await expect(page.locator("main")).toBeVisible();
  });

  test("profile shows user information", async ({ page }) => {
    await page.goto("/profile");
    // Should display email or username (adjust selector)
    await expect(page.locator("[data-testid='profile-email'], .profile-email")).toBeVisible();
  });
});
```

**Step 3: Commit**

```
feat(e2e): add profile test suite

Tests profile page loads and displays user info.
P3 priority - runs when profile code changes.
```

---

### Task 15: Add cross-suite role guard tests

**Files:**
- Modify: `frontend/e2e/auth.spec.ts`

**Step 1: Add comprehensive role guard matrix**

Append to `auth.spec.ts`:

```typescript
test.describe("Role guard matrix", () => {
  const guardTests = [
    { route: "/admin", role: "viewer", storageState: ".auth/viewer.json", expected: "/" },
    { route: "/admin", role: "editor", storageState: ".auth/editor.json", expected: "/" },
    { route: "/admin", role: "admin", storageState: ".auth/admin.json", expected: "/admin" },
    { route: "/admin/acquisitions", role: "viewer", storageState: ".auth/viewer.json", expected: "/" },
    { route: "/admin/acquisitions", role: "admin", storageState: ".auth/admin.json", expected: "/admin/acquisitions" },
    { route: "/admin/config", role: "viewer", storageState: ".auth/viewer.json", expected: "/" },
    { route: "/admin/config", role: "editor", storageState: ".auth/editor.json", expected: "/admin/config" },
    { route: "/admin/config", role: "admin", storageState: ".auth/admin.json", expected: "/admin/config" },
  ];

  for (const { route, role, storageState, expected } of guardTests) {
    test(`${role} accessing ${route} → ${expected}`, async ({ browser }) => {
      const context = await browser.newContext({ storageState });
      const page = await context.newPage();
      await page.goto(route);
      await expect(page).toHaveURL(expected);
      await context.close();
    });
  }
});
```

**Step 2: Commit**

```
feat(e2e): add comprehensive role guard matrix tests

Tests every admin route against every role to verify
correct access/redirect behavior.
```

---

## Verification Checklist

After all tasks complete:

- [ ] `npx playwright test --project=chromium` - all tests pass locally
- [ ] `npx playwright test` - all 4 browser projects pass
- [ ] Route fix verified (social-circles tests find the page)
- [ ] Auth working (tests are authenticated, not hitting login)
- [ ] Smoke tests cover all routes for all 3 roles
- [ ] Role guards correctly redirect unauthorized users
- [ ] Performance budgets work in both normal and relaxed modes
- [ ] CI workflow triggers correctly on path changes
- [ ] Post-deploy smoke runs after deployment
- [ ] `.auth/` is gitignored
- [ ] No passwords in code or logs
