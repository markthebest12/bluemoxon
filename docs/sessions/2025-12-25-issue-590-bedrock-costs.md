# Session: Issue #590 - Bedrock Cost Reporting Shows Zero

**Date:** 2025-12-25
**Issue:** <https://github.com/markthebest12/bluemoxon/issues/590>
**Status:** ✅ RESOLVED - Production restored and Bedrock costs displaying correctly

---

## Summary

Issue #590 is **RESOLVED**. Production API is healthy and Bedrock costs are displaying correctly ($63.63 MTD).

---

## What Was Fixed

**Two code/infra issues fixed:**

1. **Code:** LINKED_ACCOUNT filter doesn't work for management account (PR #591, #592)
2. **IAM:** Lambda needed `organizations:DescribeOrganization` permission (PR #593, #594)

**Collateral damage resolved:**

- Terraform state drift caused Lambda deletion during apply
- API Gateway integration updated to point to correct Lambda (`bluemoxon-prod-api`)
- Lambda permission added for API Gateway invocation

---

## PRs

| PR | Description | Status |
|----|-------------|--------|
| #591 | Code fix: Skip LINKED_ACCOUNT filter | ✅ Merged |
| #592 | Promote #591 to production | ✅ Merged |
| #593 | IAM fix: Add organizations permission | ✅ Merged |
| #594 | Promote #593 to production | ✅ Merged |
| #597 | Terraform cleanup: Update scraper image_tag | 🔄 Merged to staging, pending promotion to main |

---

## Verification (Fresh Evidence 2025-12-26)

```bash
# Production API health - VERIFIED
curl -s https://api.bluemoxon.com/api/v1/health/deep
# Result: status: healthy, version: 2025.12.25-796b8bf

# Bedrock costs - VERIFIED
bmx-api --prod GET /admin/costs
# Result: bedrock_total: 63.63 (was 0.0 before fix)
```

---

## Additional Finding: Bedrock Billing Attribution

During investigation, discovered that ALL Bedrock costs are attributed to staging account, even when production makes the calls:

| Account | Role | Bedrock Cost |
|---------|------|--------------|
| 266672885920 | Production (management) | $0.00 |
| 652617421195 | Staging (linked) | $63.63 |

**Root cause:** Unknown - appears to be AWS Organizations billing attribution quirk.

**AWS Support ticket drafted:** `docs/sessions/2025-12-25-aws-support-ticket-bedrock-billing.md`

---

## Next Steps

### Immediate (after chat compacts)

1. **Merge PR #597 to main** - Promotes scraper image_tag fix to production

   ```bash
   gh pr create --base main --head staging --title "chore: Promote scraper image_tag fix to production"
   gh pr merge <PR_NUMBER> --squash --admin
   ```

### Follow-up

2. **Submit AWS Support ticket** - Via AWS Console (billing questions are free)
   - File: `docs/sessions/2025-12-25-aws-support-ticket-bedrock-billing.md`
   - Console: <https://console.aws.amazon.com/support/home>
   - Type: Account and billing → Billing → Charges - Usage

2. **Close GitHub issue #590** - Once PR #597 is merged

   ```bash
   gh issue close 590 --comment "Resolved. Bedrock costs now displaying correctly. See session notes for details."
   ```

---

## Files Changed

- `backend/app/services/cost_explorer.py` - Management account detection + logging
- `infra/terraform/modules/lambda/main.tf` - Added organizations:DescribeOrganization IAM permission
- `infra/terraform/main.tf` - Updated scraper image_tag to existing ECR tag (PR #597)
