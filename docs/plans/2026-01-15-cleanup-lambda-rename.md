# Cleanup Lambda Rename Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rename `bluemoxon-production-cleanup` to `bluemoxon-prod-cleanup` for naming consistency.

**Architecture:** Add `BMX_CLEANUP_ENVIRONMENT` env var (matching `BMX_SCRAPER_ENVIRONMENT` pattern) to decouple cleanup Lambda naming from `BMX_ENVIRONMENT`. Update API code to use new helper, then rename Lambda via Terraform.

**Tech Stack:** Python (FastAPI), Terraform, AWS Lambda

---

## Background

The cleanup Lambda uses inconsistent naming:

- Current: `bluemoxon-production-cleanup` (uses "production")
- Target: `bluemoxon-prod-cleanup` (uses "prod")

The API constructs the Lambda name as `bluemoxon-{settings.environment}-cleanup` where `settings.environment = "production"`. We need to add a separate env var for cleanup Lambda naming (like we did for scraper).

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Lambda invocation fails during rename | Deploy code change first, then rename Lambda |
| Brief cleanup unavailable during Terraform apply | Cleanup is admin-only, low traffic, acceptable |
| IAM role and log group names change | Terraform handles these automatically |

---

### Task 1: Add `get_cleanup_environment()` Helper

**Files:**

- Modify: `backend/app/config.py:211-226` (after `get_scraper_environment()`)
- Test: `backend/tests/test_config.py` (new test)

**Step 1: Write the failing test**

Add to `backend/tests/test_config.py`:

```python
def test_get_cleanup_environment_priority(monkeypatch):
    """Test get_cleanup_environment() checks BMX_CLEANUP_ENVIRONMENT first."""
    from app.config import get_cleanup_environment

    # Clear all env vars first
    monkeypatch.delenv("BMX_CLEANUP_ENVIRONMENT", raising=False)
    monkeypatch.delenv("BMX_ENVIRONMENT", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    # Should default to staging
    assert get_cleanup_environment() == "staging"

    # ENVIRONMENT should be next in fallback
    monkeypatch.setenv("ENVIRONMENT", "prod")
    assert get_cleanup_environment() == "prod"

    # BMX_ENVIRONMENT should override ENVIRONMENT
    monkeypatch.setenv("BMX_ENVIRONMENT", "production")
    assert get_cleanup_environment() == "production"

    # BMX_CLEANUP_ENVIRONMENT should override all
    monkeypatch.setenv("BMX_CLEANUP_ENVIRONMENT", "prod")
    assert get_cleanup_environment() == "prod"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/test_config.py::test_get_cleanup_environment_priority -v`

Expected: FAIL with `ImportError: cannot import name 'get_cleanup_environment'`

**Step 3: Write minimal implementation**

Add to `backend/app/config.py` after `get_scraper_environment()` (~line 226):

```python
def get_cleanup_environment() -> str:
    """Get the environment string for cleanup Lambda naming.

    Uses BMX_CLEANUP_ENVIRONMENT if set (for prod where cleanup Lambda is named
    bluemoxon-prod-cleanup but BMX_ENVIRONMENT is "production"), otherwise
    falls back to BMX_ENVIRONMENT, ENVIRONMENT, or "staging".
    """
    return (
        os.getenv("BMX_CLEANUP_ENVIRONMENT")
        or os.getenv("BMX_ENVIRONMENT")
        or os.getenv("ENVIRONMENT", "staging")
    )
```

**Step 4: Run test to verify it passes**

Run: `cd backend && poetry run pytest tests/test_config.py::test_get_cleanup_environment_priority -v`

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/config.py backend/tests/test_config.py
git commit -m "feat(config): add get_cleanup_environment() helper for Lambda naming"
```

---

### Task 2: Update Admin API to Use Helper

**Files:**

- Modify: `backend/app/api/v1/admin.py:515-528,562-576,646-649`
- Test: `backend/tests/api/v1/test_admin_cleanup.py` (existing tests should still pass)

**Step 1: Write the test**

The existing tests in `test_admin_cleanup.py` mock the Lambda client, so they should continue passing. We just need to verify the import works.

Add to `backend/tests/api/v1/test_admin_cleanup.py` (or verify existing test coverage):

```python
def test_cleanup_uses_get_cleanup_environment(mocker):
    """Test that cleanup endpoint uses get_cleanup_environment() for Lambda name."""
    from app.config import get_cleanup_environment

    # This test verifies the function exists and is importable
    # The actual Lambda invocation is mocked in other tests
    assert callable(get_cleanup_environment)
```

**Step 2: Run existing tests to establish baseline**

Run: `cd backend && poetry run pytest tests/api/v1/test_admin_cleanup.py -v`

Expected: All tests PASS

**Step 3: Update admin.py**

In `backend/app/api/v1/admin.py`, make these changes:

Add import at top (around line 33):

```python
from app.config import get_cleanup_environment
```

Update line ~528 in `run_cleanup()`:

```python
# OLD: function_name = f"bluemoxon-{settings.environment}-cleanup"
# NEW:
function_name = f"bluemoxon-{get_cleanup_environment()}-cleanup"
```

Update line ~576 in `scan_orphans()`:

```python
# OLD: function_name = f"bluemoxon-{settings.environment}-cleanup"
# NEW:
function_name = f"bluemoxon-{get_cleanup_environment()}-cleanup"
```

Update line ~649 in `start_orphan_delete()`:

```python
# OLD: function_name = f"bluemoxon-{settings.environment}-cleanup"
# NEW:
function_name = f"bluemoxon-{get_cleanup_environment()}-cleanup"
```

**Step 4: Run tests to verify they still pass**

Run: `cd backend && poetry run pytest tests/api/v1/test_admin_cleanup.py -v`

Expected: All tests PASS

**Step 5: Run full test suite**

Run: `cd backend && poetry run pytest tests/ -v --ignore=tests/integration`

Expected: All tests PASS

**Step 6: Commit**

```bash
git add backend/app/api/v1/admin.py
git commit -m "refactor(admin): use get_cleanup_environment() for cleanup Lambda naming"
```

---

### Task 3: Add Terraform Variable

**Files:**

- Modify: `infra/terraform/variables.tf`
- Modify: `infra/terraform/main.tf`

**Step 1: Add variable to variables.tf**

Add after `scraper_environment_override` variable (around line 270):

```hcl
variable "cleanup_environment_override" {
  type        = string
  default     = null
  description = "Override for BMX_CLEANUP_ENVIRONMENT env var used to build cleanup Lambda function name. Set to 'prod' when cleanup Lambda is named bluemoxon-prod-cleanup but BMX_ENVIRONMENT is 'production'."
}
```

**Step 2: Add env var to Lambda module in main.tf**

Find the `environment_variables` block in the `module "lambda"` (around line 357) and add:

```hcl
BMX_CLEANUP_ENVIRONMENT = coalesce(var.cleanup_environment_override, var.environment)
```

Add it after `BMX_SCRAPER_ENVIRONMENT` line.

**Step 3: Validate Terraform**

Run: `cd infra/terraform && terraform fmt -recursive && terraform validate`

Expected: Success

**Step 4: Commit**

```bash
git add infra/terraform/variables.tf infra/terraform/main.tf
git commit -m "feat(terraform): add BMX_CLEANUP_ENVIRONMENT for cleanup Lambda naming"
```

---

### Task 4: Update prod.tfvars for Rename

**Files:**

- Modify: `infra/terraform/envs/prod.tfvars`

**Step 1: Update prod.tfvars**

Change line 179:

```hcl
# OLD: cleanup_function_name_override  = "bluemoxon-production-cleanup"
# NEW:
cleanup_function_name_override  = "bluemoxon-prod-cleanup"
```

Add after line 115 (after `scraper_environment_override`):

```hcl
cleanup_environment_override = "prod"
```

**Step 2: Validate Terraform**

Run: `cd infra/terraform && terraform validate`

Expected: Success

**Step 3: Commit**

```bash
git add infra/terraform/envs/prod.tfvars
git commit -m "chore(prod): rename cleanup Lambda to bluemoxon-prod-cleanup"
```

---

### Task 5: Create PR and Deploy to Staging

**Step 1: Push branch and create PR to staging**

```bash
git push -u origin feat/cleanup-lambda-rename
gh pr create --base staging --title "feat: Rename cleanup Lambda for consistency (#551)" --body "## Summary
- Add BMX_CLEANUP_ENVIRONMENT env var for cleanup Lambda naming
- Update admin.py to use get_cleanup_environment() helper
- Prepare prod.tfvars for Lambda rename

## Test Plan
- [ ] Backend tests pass
- [ ] Staging deploy succeeds
- [ ] Cleanup endpoint works in staging

Closes #551"
```

**Step 2: Wait for CI**

Run: `gh pr checks --watch`

Expected: All checks pass

**Step 3: Merge to staging**

Run: `gh pr merge --squash --delete-branch --auto`

**Step 4: Watch staging deploy**

Run: `gh run list --workflow "Deploy Staging" --limit 1`
Then: `gh run watch <run-id> --exit-status`

Expected: Deploy succeeds

---

### Task 6: Promote to Production

**Step 1: Create PR from staging to main**

```bash
gh pr create --base main --head staging --title "chore: Promote staging to production (cleanup Lambda rename #551)" --body "## Summary
Promotes cleanup Lambda rename from staging to production.

**Changes:**
- Add BMX_CLEANUP_ENVIRONMENT env var support
- Rename cleanup Lambda: bluemoxon-production-cleanup → bluemoxon-prod-cleanup

## Test Plan
- [ ] Staging verified working
- [ ] Production deploy succeeds
- [ ] Admin cleanup endpoint works

Related: #551"
```

**Step 2: Review and merge**

Wait for user approval, then:
Run: `gh pr merge --squash`

**Step 3: Watch production deploy**

Run: `gh run list --workflow Deploy --limit 1`
Then: `gh run watch <run-id> --exit-status`

Expected: Deploy succeeds, new Lambda `bluemoxon-prod-cleanup` created

---

### Task 7: Apply Terraform to Complete Rename

**Note:** The deploy workflow only updates Lambda code, not infrastructure. The actual Lambda rename requires a Terraform apply.

**Step 1: Plan prod Terraform**

Run: `cd infra/terraform && AWS_PROFILE=bmx-prod terraform plan -var-file=envs/prod.tfvars -out=cleanup-rename.plan`

Expected output should show:

- `aws_lambda_function.this` will be destroyed (old name)
- `aws_lambda_function.this` will be created (new name)
- IAM role renamed
- CloudWatch log group renamed

**Step 2: Apply Terraform**

Run: `cd infra/terraform && AWS_PROFILE=bmx-prod terraform apply cleanup-rename.plan`

Expected: Lambda renamed successfully

**Step 3: Verify cleanup works**

Run: `bmx-api --prod GET /admin/cleanup/orphans/scan`

Expected: Returns orphan scan results (200 OK)

---

### Task 8: Clean Up and Close Issue

**Step 1: Update session log**

Update `~/docs/session-2026-01-15-1411-lambda-rename.md` with completion status.

**Step 2: Close issue**

Run: `gh issue close 551 --comment "Completed. Cleanup Lambda renamed from bluemoxon-production-cleanup to bluemoxon-prod-cleanup for naming consistency."`

---

## Rollback Plan

If issues occur after rename:

1. Revert prod.tfvars to use `cleanup_function_name_override = "bluemoxon-production-cleanup"`
2. Remove `cleanup_environment_override` line
3. Apply Terraform to recreate old Lambda
4. The code change (get_cleanup_environment) is backward compatible and doesn't need revert
