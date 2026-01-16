# Cognito Sync Implementation Plan

**Date:** 2025-12-08
**Status:** Ready for Implementation
**Decision:** Option B - Separate Cognito with on-demand user sync

## Overview

Add opt-in Cognito user mapping to the existing `db_sync` Lambda. After DB sync, update `users.cognito_sub` to match staging Cognito subs (matched by email).

## Design Decisions

| Question | Decision |
|----------|----------|
| When to run? | Opt-in via `sync_cognito: true` in event payload |
| Missing users? | Skip and log warning (don't auto-create) |
| Cognito pool config? | Environment variable `COGNITO_USER_POOL_ID` |
| Execution order? | After DB sync completes |

## Tasks

### Task 1: Add Terraform variable for Cognito pool ID

**File:** `infra/terraform/modules/db-sync-lambda/variables.tf`

Add variable:

```hcl
variable "cognito_user_pool_id" {
  description = "Staging Cognito user pool ID for user mapping after DB sync"
  type        = string
  default     = ""
}
```

**Verification:** `terraform validate`

### Task 2: Add environment variable to Lambda

**File:** `infra/terraform/modules/db-sync-lambda/main.tf`

Add to Lambda environment variables block:

```hcl
COGNITO_USER_POOL_ID = var.cognito_user_pool_id
```

**Verification:** `terraform validate`

### Task 3: Add IAM permission for Cognito ListUsers

**File:** `infra/terraform/modules/db-sync-lambda/main.tf`

Add statement to Lambda IAM policy:

```hcl
statement {
  effect    = "Allow"
  actions   = ["cognito-idp:ListUsers"]
  resources = [
    "arn:aws:cognito-idp:*:*:userpool/${var.cognito_user_pool_id}"
  ]
}
```

Note: Only add if `cognito_user_pool_id` is not empty (use dynamic block or condition).

**Verification:** `terraform validate`

### Task 4: Pass Cognito pool ID from main.tf

**File:** `infra/terraform/main.tf`

Update db_sync_lambda module call:

```hcl
module "db_sync_lambda" {
  # ... existing ...
  cognito_user_pool_id = module.cognito.user_pool_id
}
```

**Verification:** `terraform plan -var-file=envs/staging.tfvars` shows expected changes

### Task 5: Implement sync_cognito_users function in handler

**File:** `backend/lambdas/db_sync/handler.py`

Add function:

```python
def sync_cognito_users(staging_conn, user_pool_id: str) -> dict:
    """Update users.cognito_sub to match staging Cognito subs by email."""
    results = {
        "updated": 0,
        "skipped_no_cognito_user": 0,
        "skipped_no_db_user": 0,
        "details": []
    }

    # 1. List all users from staging Cognito
    cognito = boto3.client("cognito-idp")
    cognito_users = {}  # email -> sub

    paginator = cognito.get_paginator("list_users")
    for page in paginator.paginate(UserPoolId=user_pool_id):
        for user in page["Users"]:
            email = next((a["Value"] for a in user["Attributes"] if a["Name"] == "email"), None)
            if email:
                cognito_users[email.lower()] = user["Username"]

    logger.info(f"Found {len(cognito_users)} users in Cognito pool {user_pool_id}")

    # 2. Get all users from staging DB
    with staging_conn.cursor() as cur:
        cur.execute("SELECT id, email, cognito_sub FROM users WHERE email IS NOT NULL")
        db_users = cur.fetchall()

    # 3. Update cognito_sub for matching users
    for user_id, email, old_sub in db_users:
        email_lower = email.lower()
        if email_lower in cognito_users:
            new_sub = cognito_users[email_lower]
            if old_sub != new_sub:
                with staging_conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET cognito_sub = %s WHERE id = %s",
                        (new_sub, user_id)
                    )
                staging_conn.commit()
                results["updated"] += 1
                results["details"].append({
                    "email": email,
                    "status": "updated",
                    "old_sub": old_sub,
                    "new_sub": new_sub
                })
                logger.info(f"Updated cognito_sub for {email}: {old_sub} -> {new_sub}")
        else:
            results["skipped_no_cognito_user"] += 1
            results["details"].append({
                "email": email,
                "status": "skipped",
                "reason": "no_cognito_user"
            })

    # 4. Log Cognito users without DB entries (informational)
    db_emails = {row[1].lower() for row in db_users if row[1]}
    for cognito_email in cognito_users:
        if cognito_email not in db_emails:
            results["skipped_no_db_user"] += 1
            results["details"].append({
                "email": cognito_email,
                "status": "skipped",
                "reason": "no_db_user"
            })

    return results
```

**Verification:** `cd backend && poetry run ruff check lambdas/db_sync/handler.py`

### Task 6: Call sync_cognito_users from handler

**File:** `backend/lambdas/db_sync/handler.py`

Update `handler()` function to:

1. Check for `sync_cognito` in event payload
2. Get `COGNITO_USER_POOL_ID` from environment
3. Call `sync_cognito_users()` after DB sync
4. Add results to response

**Verification:** `cd backend && poetry run ruff check lambdas/db_sync/handler.py`

### Task 7: Apply Terraform changes

```bash
cd infra/terraform
terraform plan -var-file=envs/staging.tfvars
terraform apply -var-file=envs/staging.tfvars
```

**Verification:** Lambda env vars include `COGNITO_USER_POOL_ID`

### Task 8: Deploy Lambda code

The db_sync Lambda code needs to be redeployed with the new handler.

```bash
./scripts/deploy-db-sync-lambda.sh --update
```

**Verification:** Check Lambda console shows updated code

### Task 9: Test the sync

```bash
# Run sync without Cognito mapping (should work as before)
aws lambda invoke --function-name bluemoxon-staging-db-sync \
    --profile staging --payload '{}' .tmp/sync-response.json
cat .tmp/sync-response.json | jq

# Run sync WITH Cognito mapping
aws lambda invoke --function-name bluemoxon-staging-db-sync \
    --profile staging --payload '{"sync_cognito": true}' .tmp/sync-response.json
cat .tmp/sync-response.json | jq '.body | fromjson | .results.cognito_mapping'
```

**Verification:** Response shows updated users count > 0

### Task 10: Test login

Try logging in at <https://staging.app.bluemoxon.com> with <mjramos76@gmail.com>

**Verification:** Login succeeds

### Task 11: Update documentation

1. Update `docs/DATABASE_SYNC.md` with new `sync_cognito` flag
2. Update `docs/plans/2025-12-08-staging-auth-investigation.md` status to resolved
3. Update `CLAUDE.md` with staging auth guidance

## Files to Modify

| File | Change |
|------|--------|
| `infra/terraform/modules/db-sync-lambda/variables.tf` | Add `cognito_user_pool_id` variable |
| `infra/terraform/modules/db-sync-lambda/main.tf` | Add env var and IAM permission |
| `infra/terraform/main.tf` | Pass Cognito pool ID to module |
| `backend/lambdas/db_sync/handler.py` | Add `sync_cognito_users()` and call from handler |
| `docs/DATABASE_SYNC.md` | Document new flag |
| `docs/plans/2025-12-08-staging-auth-investigation.md` | Mark resolved |
| `CLAUDE.md` | Add staging auth guidance |
