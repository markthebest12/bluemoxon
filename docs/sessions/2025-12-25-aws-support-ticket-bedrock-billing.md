# AWS Support Ticket: Bedrock Cost Attribution Issue

## How to Submit

1. Go to AWS Console → Support Center → Create case
2. Select: **Account and billing**
3. Service: **Billing**
4. Category: **Charges - Usage**
5. Copy content below into the case

---

## Subject

Bedrock costs incorrectly attributed to linked account instead of calling account

## Description

We have two AWS accounts in an AWS Organization:
- **Management account:** 266672885920 (production)
- **Linked account:** 652617421195 (staging)

Both accounts invoke Amazon Bedrock (Claude models) from Lambda functions. However, ALL Bedrock costs are being attributed to the staging account (652617421195), even when production Lambda functions make the calls.

### Evidence

**CloudWatch Logs confirm production invocations:**
- Dec 13, 2025: bluemoxon-prod-analysis-worker invoked Bedrock (book 16)
- Dec 15, 2025: bluemoxon-prod-analysis-worker invoked Bedrock (book 490)

**Cost Explorer shows $0 for production Bedrock:**
```
Account 266672885920 (prod): $0.00 Bedrock costs
Account 652617421195 (staging): $63.63 Bedrock costs
```

Even on Dec 15 when production Lambda DID invoke Bedrock, the cost shows as $0 for production.

### Configuration (both accounts identical)

- Model IDs used:
  - us.anthropic.claude-sonnet-4-5-20250929-v1:0
  - us.anthropic.claude-opus-4-5-20251101-v1:0
  - anthropic.claude-3-haiku-20240307-v1:0
- Region: us-west-2
- Model access: Authorized in both accounts
- IAM: Standard Lambda execution roles with bedrock:InvokeModel
- No cross-account role assumptions

### Questions

1. Why are Bedrock costs from production account (266672885920) being attributed to staging account (652617421195)?
2. Is this expected behavior for AWS Organizations with Bedrock?
3. How can we ensure each account's Bedrock usage is billed to that account?

### Impact

We cannot accurately track Bedrock costs per environment, which affects:
- Cost allocation and budgeting
- Environment-specific usage monitoring
- Chargeback reporting

Thank you for investigating this billing attribution issue.
