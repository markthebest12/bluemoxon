# Cross-Account Secrets & Post-Deploy Validation Design

**Date:** 2024-12-09
**Status:** Approved
**Context:** Lessons learned from staging Terraform conformance test (destroy/apply cycle)

## Problem Statement

Two related issues discovered during staging infrastructure rebuild:

1. **Database sync fails** - The db-sync Lambda cannot access prod database credentials because the prod secret is encrypted with the default AWS KMS key (`aws/secretsmanager`), which doesn't support cross-account access.

2. **No automated validation** - After terraform rebuild, multiple manual steps are required (trigger deploy workflow, update config files, run db-sync, check health). No automated way to verify everything works.

## Design Goals

- **Security**: Prod credentials stay in prod account (read-only access from staging)
- **Automation**: DB sync "just works" without manual credential management
- **Maintainability**: Credential rotation in prod automatically propagates to staging
- **Validation**: Full automated validation after every staging deploy

## Solution Overview

### Part 1: Cross-Account Secrets Module

A Terraform module that creates a customer-managed KMS key with cross-account decrypt permissions, enabling staging's db-sync Lambda to read prod secrets directly.

### Part 2: Post-Deploy Validation Suite

Comprehensive validation integrated into the staging deploy workflow:

- Infrastructure tests (VPC endpoints, Lambda, S3)
- Deep health check (all components healthy)
- API smoke tests (core endpoints work)
- E2E browser tests (full user flow)

---

## Part 1: Cross-Account Secrets Module

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Prod Account (266672885920)                   │
│                                                                  │
│  ┌──────────────────────┐    ┌─────────────────────────────┐    │
│  │ KMS Key              │    │ Secrets Manager             │    │
│  │ bluemoxon-cross-     │◄───│ bluemoxon/db-credentials    │    │
│  │ account-secrets      │    │ (encrypted with CMK)        │    │
│  │                      │    └─────────────────────────────┘    │
│  │ Key Policy:          │                                       │
│  │ - Allow staging      │                                       │
│  │   account decrypt    │                                       │
│  └──────────┬───────────┘                                       │
└─────────────│───────────────────────────────────────────────────┘
              │ kms:Decrypt
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Staging Account (652617421195)                  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Lambda: bluemoxon-staging-db-sync                         │   │
│  │                                                           │   │
│  │ IAM Role has:                                             │   │
│  │ - secretsmanager:GetSecretValue on prod secret ARN        │   │
│  │ - kms:Decrypt on prod KMS key ARN                         │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Module Interface

```hcl
# In prod account terraform
module "cross_account_secrets" {
  source = "./modules/cross-account-secrets"

  key_alias = "bluemoxon-cross-account-secrets"

  # Secrets to make available cross-account
  secret_arns = [
    "arn:aws:secretsmanager:us-west-2:266672885920:secret:bluemoxon/db-credentials-*"
  ]

  # Accounts/roles allowed to decrypt
  consumer_account_ids = ["652617421195"]  # staging account
  consumer_role_arns = [
    "arn:aws:iam::652617421195:role/bluemoxon-staging-db-sync"
  ]
}
```

### Module Files

```
infra/terraform/modules/cross-account-secrets/
├── main.tf           # KMS key resource with cross-account policy
├── variables.tf      # key_alias, secret_arns, consumer_account_ids, consumer_role_arns
├── outputs.tf        # kms_key_arn, kms_key_id, kms_key_alias_arn
└── README.md         # Usage documentation
```

### KMS Key Policy (main.tf excerpt)

```hcl
resource "aws_kms_key" "cross_account" {
  description             = "KMS key for cross-account secret access"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowRootAccountFullAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowCrossAccountDecrypt"
        Effect = "Allow"
        Principal = {
          AWS = var.consumer_role_arns
        }
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })
}
```

### Staging IAM Policy Addition

```hcl
# Add to db-sync Lambda IAM role
resource "aws_iam_role_policy" "cross_account_secret_access" {
  name = "cross-account-secret-access"
  role = aws_iam_role.db_sync_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "secretsmanager:GetSecretValue"
        Resource = var.prod_database_secret_arn
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = var.prod_kms_key_arn
      }
    ]
  })
}
```

### Implementation Steps

1. Create `modules/cross-account-secrets` module
2. Apply to prod account (creates KMS key with cross-account policy)
3. Re-encrypt prod secret: `aws secretsmanager update-secret --secret-id bluemoxon/db-credentials --kms-key-id alias/bluemoxon-cross-account-secrets`
4. Add IAM policy to staging db-sync Lambda role
5. Apply to staging account
6. Test: `aws lambda invoke --function-name bluemoxon-staging-db-sync ...`

---

## Part 2: Post-Deploy Validation Suite

### Validation Levels

| Level | Name | Duration | What it Tests |
|-------|------|----------|---------------|
| 1 | Infrastructure | ~30s | VPC endpoints, Lambda invoke, S3 access |
| 2 | Deep Health | ~5s | `/api/v1/health/deep` all components healthy |
| 3 | Smoke Tests | ~30s | Core API endpoints return expected data |
| 4 | E2E Tests | ~2-3min | Full browser flow: login, view data, images |

### Workflow Structure

```yaml
# .github/workflows/deploy-staging.yml
name: Deploy to Staging

on:
  push:
    branches: [staging]

jobs:
  # Existing jobs...
  deploy:
    # ... deploy Lambda, frontend, etc.

  sync-database:
    needs: deploy
    runs-on: ubuntu-latest
    steps:
      - name: Check if DB needs sync
        id: check
        run: |
          RESPONSE=$(curl -s https://staging.api.bluemoxon.com/api/v1/health/deep)
          if echo "$RESPONSE" | grep -q "relation.*does not exist"; then
            echo "needs_sync=true" >> $GITHUB_OUTPUT
          else
            echo "needs_sync=false" >> $GITHUB_OUTPUT
          fi

      - name: Trigger DB sync
        if: steps.check.outputs.needs_sync == 'true'
        run: |
          aws lambda invoke \
            --function-name bluemoxon-staging-db-sync \
            --payload '{}' \
            response.json
          cat response.json

      - name: Wait for sync completion
        if: steps.check.outputs.needs_sync == 'true'
        run: |
          for i in {1..60}; do
            RESPONSE=$(curl -s https://staging.api.bluemoxon.com/api/v1/health/deep)
            if echo "$RESPONSE" | jq -e '.checks.database.status == "healthy"' > /dev/null; then
              echo "Database sync complete!"
              exit 0
            fi
            echo "Waiting for DB sync... ($i/60)"
            sleep 10
          done
          echo "DB sync timed out"
          exit 1

  validate-infrastructure:
    needs: sync-database
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run infrastructure validation
        run: ./scripts/validate-infrastructure.sh
        env:
          AWS_REGION: us-west-2

  validate-health:
    needs: validate-infrastructure
    runs-on: ubuntu-latest
    steps:
      - name: Deep health check
        run: |
          RESPONSE=$(curl -sf https://staging.api.bluemoxon.com/api/v1/health/deep)
          echo "$RESPONSE" | jq .
          STATUS=$(echo "$RESPONSE" | jq -r '.status')
          if [ "$STATUS" != "healthy" ]; then
            echo "Health check failed!"
            exit 1
          fi

  validate-smoke:
    needs: validate-health
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run smoke tests
        run: ./scripts/smoke-tests.sh

  validate-e2e:
    needs: validate-smoke
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Install Playwright
        run: npx playwright install --with-deps chromium
      - name: Run E2E tests
        run: npx playwright test tests/e2e/staging-validation.spec.ts
        env:
          STAGING_URL: https://staging.app.bluemoxon.com
          TEST_USER_EMAIL: ${{ secrets.STAGING_TEST_USER_EMAIL }}
          TEST_USER_PASSWORD: ${{ secrets.STAGING_TEST_USER_PASSWORD }}
      - name: Upload screenshots on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-screenshots
          path: test-results/
```

### Scripts

#### scripts/validate-infrastructure.sh

```bash
#!/bin/bash
set -euo pipefail

echo "=== Infrastructure Validation ==="

# Test Lambda can be invoked
echo "Testing Lambda invocation..."
aws lambda invoke \
  --function-name bluemoxon-staging-api \
  --payload '{"path": "/health", "httpMethod": "GET"}' \
  --cli-binary-format raw-in-base64-out \
  response.json
cat response.json | jq .

# Test S3 bucket exists
echo "Testing S3 access..."
aws s3 ls s3://bluemoxon-images-staging --max-items 1

echo "=== Infrastructure validation passed ==="
```

#### scripts/smoke-tests.sh

```bash
#!/bin/bash
set -euo pipefail

BASE_URL="https://staging.api.bluemoxon.com/api/v1"

echo "=== API Smoke Tests ==="

# Test books endpoint
echo "Testing GET /books..."
RESPONSE=$(curl -sf "$BASE_URL/books?limit=1")
echo "$RESPONSE" | jq .
COUNT=$(echo "$RESPONSE" | jq '.items | length')
if [ "$COUNT" -lt 1 ]; then
  echo "ERROR: Books endpoint returned no data"
  exit 1
fi

# Test version endpoint
echo "Testing GET /health/version..."
VERSION=$(curl -sf "$BASE_URL/health/version" | jq -r '.version')
echo "Version: $VERSION"

# Test image URLs return images
echo "Testing image URLs..."
IMAGE_URL=$(echo "$RESPONSE" | jq -r '.items[0].primary_image_url // empty')
if [ -n "$IMAGE_URL" ]; then
  CONTENT_TYPE=$(curl -sI "$IMAGE_URL" | grep -i "content-type" | head -1)
  echo "Image Content-Type: $CONTENT_TYPE"
  if ! echo "$CONTENT_TYPE" | grep -qi "image/"; then
    echo "ERROR: Image URL did not return image content type"
    exit 1
  fi
fi

# Test CORS headers
echo "Testing CORS headers..."
CORS=$(curl -sI "$BASE_URL/health" | grep -i "access-control-allow-origin" || echo "")
if [ -z "$CORS" ]; then
  echo "WARNING: No CORS headers found"
fi

echo "=== Smoke tests passed ==="
```

#### tests/e2e/staging-validation.spec.ts

```typescript
import { test, expect } from '@playwright/test';

const STAGING_URL = process.env.STAGING_URL || 'https://staging.app.bluemoxon.com';

test.describe('Staging Validation', () => {
  test('homepage loads', async ({ page }) => {
    await page.goto(STAGING_URL);
    await expect(page).toHaveTitle(/BlueMoxon/);
  });

  test('books list renders', async ({ page }) => {
    await page.goto(STAGING_URL);
    // Wait for books to load
    await page.waitForSelector('[data-testid="book-card"]', { timeout: 10000 });
    const books = await page.locator('[data-testid="book-card"]').count();
    expect(books).toBeGreaterThan(0);
  });

  test('images load correctly', async ({ page }) => {
    await page.goto(STAGING_URL);
    await page.waitForSelector('[data-testid="book-card"]');

    // Check first image loads
    const img = page.locator('[data-testid="book-card"] img').first();
    await expect(img).toBeVisible();

    // Verify image actually loaded (not broken)
    const naturalWidth = await img.evaluate((el: HTMLImageElement) => el.naturalWidth);
    expect(naturalWidth).toBeGreaterThan(0);
  });

  test('login flow works', async ({ page }) => {
    const email = process.env.TEST_USER_EMAIL;
    const password = process.env.TEST_USER_PASSWORD;

    if (!email || !password) {
      test.skip();
      return;
    }

    await page.goto(`${STAGING_URL}/login`);
    await page.fill('[name="email"]', email);
    await page.fill('[name="password"]', password);
    await page.click('[type="submit"]');

    // Should redirect to home after login
    await page.waitForURL(STAGING_URL + '/**', { timeout: 10000 });

    // Should see user menu or logout option
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
  });
});
```

---

## New Files Summary

```
infra/terraform/modules/cross-account-secrets/
├── main.tf
├── variables.tf
├── outputs.tf
└── README.md

scripts/
├── validate-infrastructure.sh
└── smoke-tests.sh

tests/e2e/
└── staging-validation.spec.ts

.github/workflows/
└── deploy-staging.yml  (modified)
```

## Files Modified

- `infra/terraform/envs/prod.tfvars` - Add cross-account-secrets module reference
- `infra/terraform/envs/staging.tfvars` - Add prod KMS key ARN variable
- `infra/terraform/modules/db-sync-lambda/main.tf` - Add cross-account IAM policy

## Implementation Phases

### Phase 1: Cross-Account Secrets (Prerequisite)

1. Create `modules/cross-account-secrets` Terraform module
2. Apply to prod account (creates KMS key)
3. Re-encrypt prod secret with new KMS key
4. Apply to staging account (grants IAM permissions)
5. Test: Invoke db-sync Lambda, verify it succeeds

### Phase 2: Enhanced Smoke Tests

1. Create `scripts/validate-infrastructure.sh`
2. Create `scripts/smoke-tests.sh`
3. Add to deploy-staging.yml after deploy job
4. Test: Deploy to staging, verify new tests run

### Phase 3: E2E Tests

1. Create `tests/e2e/staging-validation.spec.ts`
2. Add Playwright setup to workflow
3. Configure test user credentials in GitHub Secrets
4. Add screenshot capture on failure
5. Test: Run full workflow, verify E2E passes

### Phase 4: Auto DB-Sync

1. Add "check if DB empty" step to workflow
2. Add "trigger db-sync" conditional step
3. Add "wait for sync" with timeout
4. Test: Full terraform destroy/apply cycle validates automatically

## Success Criteria

After implementation:

```bash
# Full staging rebuild should "just work"
cd infra/terraform
terraform destroy -var-file=envs/staging.tfvars
terraform apply -var-file=envs/staging.tfvars

# Push to staging triggers:
# 1. Deploy workflow runs
# 2. DB-sync auto-triggers (detects empty DB)
# 3. All 4 validation levels pass
# 4. Workflow shows green checkmark
```

## Security Considerations

- Prod credentials never stored in staging account
- Read-only access (decrypt only, no write/modify)
- Specific IAM role restriction (only db-sync Lambda)
- CloudTrail audit logging for all cross-account access
- KMS key rotation enabled

## Rollback Plan

If issues arise:

1. Revert to direct environment variables (PROD_DB_HOST/USER/PASSWORD)
2. Remove cross-account IAM policies
3. KMS key can be disabled but not immediately deleted (30-day window)
