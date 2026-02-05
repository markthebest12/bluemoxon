# Production Profile Worker Deploy & Validation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Promote staging to main, apply terraform to production to update Bedrock IAM policies, then validate the profile-worker SQS pipeline end-to-end with progressive batch sizes.

**Architecture:** Three staging commits (#1606 IAM fix, concurrency=5, #1609 job progress fix) need promotion to main via merge PR. Production terraform apply updates IAM policies. Then 4-step progressive SQS validation: single → batch 6 → batch 20 → full generation.

**Tech Stack:** GitHub CLI, Terraform (AWS), SQS, Lambda, Bedrock, bmx-api CLI

**Current State:**
- Staging: 3 commits ahead of main (7056015f, 4d475f88, 17043d6b)
- Production: profile-worker Lambda exists (terraform applied earlier), layer manually attached, concurrency=5 applied, but Bedrock IAM still broken (missing Haiku model ID)
- Production SQS queue: purged (empty)

---

### Task 1: Promote staging → main

**Step 1: Create promotion PR**

Run:
```bash
gh pr create --base main --head staging --title "chore: Promote staging — profile worker fixes"
```

**Step 2: Watch CI**

Run:
```bash
gh pr checks <PR_NUMBER> --watch
```

Expected: All checks pass (or non-required checks skip/fail as expected).

**Step 3: Merge with --merge (NOT squash)**

Run:
```bash
gh pr merge <PR_NUMBER> --merge
```

Per CLAUDE.md: promotions use `--merge` to preserve commit identity.

**Step 4: Watch deploy**

Run:
```bash
gh run list --workflow Deploy --branch main --limit 1
gh run watch <RUN_ID> --exit-status
```

Expected: Deploy succeeds. Profile worker Lambda gets updated code + layer attached.

**Step 5: Verify deploy — profile worker Lambda has layer and new code**

Run:
```bash
AWS_PROFILE=bmx-prod aws lambda get-function \
  --function-name bluemoxon-prod-profile-worker \
  --query 'Configuration.{Layers:Layers[*].Arn,LastModified:LastModified}'
```

Expected: Layer ARN present, LastModified is recent (after deploy).

---

### Task 2: Terraform apply to production

**Step 1: Initialize terraform with production backend**

Run:
```bash
cd infra/terraform
AWS_PROFILE=bmx-prod terraform init -backend-config=backends/prod.hcl -reconfigure
```

**Step 2: Plan and review changes**

Run:
```bash
export TF_VAR_api_key=$(AWS_PROFILE=bmx-prod aws secretsmanager get-secret-value --secret-id bluemoxon-prod/api-key --query SecretString --output text)
AWS_PROFILE=bmx-prod terraform plan -var-file=envs/prod.tfvars
```

Expected: Changes to Bedrock IAM policies for all worker modules (updating `bedrock_model_ids` to include Haiku). Should be updates in-place only — NO new resources, NO destroys (profile-worker infra already exists on prod from earlier apply).

**Step 3: Apply**

Run:
```bash
AWS_PROFILE=bmx-prod terraform apply -var-file=envs/prod.tfvars -auto-approve
```

**Step 4: Switch terraform back to staging backend**

Run:
```bash
AWS_PROFILE=bmx-staging terraform init -backend-config=backends/staging.hcl -reconfigure
```

This prevents accidentally running staging commands against production state.

---

### Task 3: Validate single SQS message on production

**Step 1: Verify production health**

Run:
```bash
bmx-api --prod GET /health/deep
```

Expected: All checks healthy, profile_generation queue present with 0 messages.

**Step 2: Send single profile generation message**

Pick an entity that doesn't have a profile yet (NOT author:31 EBB which was generated earlier via sync endpoint).

Run:
```bash
AWS_PROFILE=bmx-prod aws sqs send-message \
  --queue-url "<PROD_PROFILE_QUEUE_URL>" \
  --message-body '{"job_id":"prod-test-001","entity_type":"author","entity_id":1,"owner_id":1}'
```

Note: Get queue URL from health check response or terraform output.

**Step 3: Wait 20s, check Lambda logs**

Run:
```bash
AWS_PROFILE=bmx-prod aws logs tail /aws/lambda/bluemoxon-prod-profile-worker --since 2m --format short
```

Expected: START, no ERROR lines, END, REPORT with ~10-20s duration (Bedrock call).

**Step 4: Verify profile generated**

Run:
```bash
bmx-api --prod GET /entity/author/1/profile
```

Expected: `bio_summary` is not null, `generated_at` is recent, `model_version` shows Haiku.

---

### Task 4: Validate batch of 6 (concurrency test)

**Step 1: Send 6 messages for different entities**

Run:
```bash
QUEUE_URL="<PROD_PROFILE_QUEUE_URL>"
for i in <6_ENTITY_IDS_WITHOUT_PROFILES>; do
  AWS_PROFILE=bmx-prod aws sqs send-message \
    --queue-url "$QUEUE_URL" \
    --message-body "{\"job_id\":\"prod-batch6-001\",\"entity_type\":\"author\",\"entity_id\":$i,\"owner_id\":1}" \
    --output text --query 'MessageId'
done
```

**Step 2: Monitor queue drain**

Run (every 15s):
```bash
AWS_PROFILE=bmx-prod aws sqs get-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible \
  --query 'Attributes'
```

Expected: Messages move from visible → not-visible → 0. Should drain in ~30s (5 concurrent, 1 queued).

**Step 3: Verify no errors in logs**

Run:
```bash
AWS_PROFILE=bmx-prod aws logs tail /aws/lambda/bluemoxon-prod-profile-worker --since 3m --format short | grep ERROR
```

Expected: 0 errors.

**Step 4: Spot-check profiles**

Run:
```bash
bmx-api --prod GET /entity/author/<ID>/profile
```

Expected: All 6 have bio_summary populated.

---

### Task 5: Validate batch of 20

**PREREQUISITE:** Task 4 must be FULLY complete — all 6 messages processed by Bedrock, queue at 0.

**Step 1: Send 20 messages for entities without profiles**

Same pattern as Task 4 but with 20 entity IDs.

**Step 2: Monitor queue drain**

Expected: ~4 waves of 5 concurrent, total drain in ~60-90s.

**Step 3: Verify no errors**

Same as Task 4 Step 3.

**Step 4: Spot-check profiles**

Check 5-6 random profiles from the batch.

---

### Task 6: Run full batch generation

**PREREQUISITE:** Task 5 must be FULLY complete — all 20 messages processed, 0 errors.

**Step 1: Trigger full generation**

Run:
```bash
bmx-api --prod POST /entity/profiles/generate-all
```

Expected: Returns `{"job_id": "...", "total_entities": N, "status": "in_progress"}`.

**Step 2: Monitor job progress**

Run (every 30s):
```bash
bmx-api --prod GET /entity/profiles/generate-all/status/<JOB_ID>
```

Expected: `succeeded` count increases, `failed` stays low. With 264 entities at concurrency=5 and ~15s per Bedrock call, full batch takes ~13 minutes.

**Step 3: Verify completion**

Expected: Status becomes "completed", succeeded + failed = total_entities.

**Step 4: Verify DLQ is empty**

Run:
```bash
AWS_PROFILE=bmx-prod aws sqs get-queue-attributes \
  --queue-url "<PROD_PROFILE_DLQ_URL>" \
  --attribute-names ApproximateNumberOfMessages \
  --query 'Attributes.ApproximateNumberOfMessages'
```

Expected: 0 messages.

---

### Task 7: Close issues

**Step 1: Close #1605 (missing layer) with process note**

```bash
gh issue close 1605 --comment "Resolved: terraform apply must precede first deploy for new Lambda functions. Layer now attached by deploy workflow. No code change needed."
```

**Step 2: Close #1606 (Bedrock IAM)**

```bash
gh issue close 1606 --comment "Fixed by PR #1608 — extracted bedrock_model_ids to locals.tf, all worker modules now use shared list including Haiku model ID."
```

**Step 3: Close #1607 (concurrency)**

```bash
gh issue close 1607 --comment "Fixed by commit 7056015f — reserved_concurrency set to 5 for profile-worker Lambda."
```

---

### Task 8: Create GitHub issue for new bug #1609

The `_update_job_progress` TypeError was discovered during staging testing and fixed. Log it properly.

**Step 1: Create issue**

```bash
gh issue create \
  --title "fix: profile worker job progress tracking TypeError" \
  --body "SQLAlchemy .values(**dict) requires string keys, but increment dict used column objects. Fixed by passing dict as positional arg. PR #1609." \
  --label "bug,entity-profiles"
```

**Step 2: Immediately close it (already fixed)**

```bash
gh issue close <NUMBER> --comment "Fixed by PR #1609"
```
