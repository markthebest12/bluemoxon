# Session: Artifacts Bucket Implementation

**Date:** 2026-01-07
**Design:** `docs/plans/2026-01-07-artifacts-bucket-design.md`

## Objective

Implement separate S3 bucket for Lambda artifacts to eliminate race condition between frontend sync (`--delete`) and Lambda deploys.

## Session Rules

1. PRs need user review before staging and production
2. Simple single-line bash commands only (no `&&`, `\`, `$(...)`, `#` comments, `!`)
3. Use `bmx-api` for API calls
4. Always use superpowers skills including TDD
5. Maximize parallelism with subagents

## Progress

- [x] Phase 1: Terraform (staging) - Tasks 1-4 (PR #910)
- [ ] Phase 2: Workflow (staging) - Tasks 5-8 (after Terraform applied)
- [ ] Phase 3: Production - Terraform apply + merge to main
- [ ] Phase 4: Cleanup - Delete old lambda/* from frontend buckets

## Log

### 2026-01-07

- Session started
- Read design document (8 tasks ready for implementation)
- Implemented all 8 tasks in PR #909
- **Code review identified P0 blocking issue:** chicken-and-egg deployment problem
  - Workflow reads `artifacts_bucket_name` from Terraform output
  - On first deploy, Terraform hasn't created bucket yet
  - All S3 operations would fail
- **Resolution:** Split into two PRs
  - PR #909 closed
  - PR #910: Terraform only (create bucket + IAM before workflow changes)
  - PR #909b (pending): Workflow changes (after Terraform applied)
- **Additional fixes from review:**
  - Added `s3:DeleteObject` permission to IAM policy
  - Changed `enable_versioning = true` for artifact rollback capability

---

## Notes

**Correct deployment sequence:**

1. Merge PR #910 (Terraform) to staging
2. Apply Terraform: `AWS_PROFILE=bmx-staging terraform apply -var-file=envs/staging.tfvars`
3. Verify bucket: `aws s3 ls s3://bluemoxon-artifacts-staging/`
4. THEN create and merge workflow PR
