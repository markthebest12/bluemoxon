# Infrastructure Issue Triage - January 2026

## Context

Comprehensive review of open infrastructure issues using AWS Well-Architected Framework principles and cost-benefit analysis. Goal: rationalize technical debt and close low-value work to focus on Bedrock/AI features.

## Review Criteria

- **Actual pain**: Has this issue caused real problems?
- **Cost-benefit**: Does the fix justify the effort and risk?
- **Strategic alignment**: Does this support where the product is going?

## Decisions

### Close as "Won't Fix" (7 issues)

#### Carrier Tracking Feature (likely cut) - 4 issues

The carrier tracking feature (#516) is being deprioritized. These dependent issues should be closed:

| Issue | Title | Reason |
|-------|-------|--------|
| #792 | Deploy tracking worker infrastructure | Feature likely cut |
| #790 | CloudWatch metrics for carrier health | Feature likely cut |
| #786 | Configure SES/SNS for notifications | Feature likely cut |
| #784 | SSM Parameter Store for carrier credentials | Feature likely cut |

#### Theoretical Improvements (no actual pain) - 3 issues

| Issue | Title | Reason |
|-------|-------|--------|
| #477 | RDS Aurora pause scheduling | Staging RDS is db.t3.micro (~$13/mo). Claimed savings don't match actual costs. No pain. |
| #476 | Bedrock VPC endpoint to remove NAT | NAT Gateway already disabled in prod. Staging NAT costs minimal with usage pattern. |
| #559 | Terraform state checksum mismatch | One-time incident (Dec 2025), hasn't recurred in months. Not worth automation. |

### Convert to "Low Priority" (1 issue)

| Issue | Title | Reason |
|-------|-------|--------|
| #551 | Production Lambda rename | Causes minor debugging friction (inconsistent naming). However, fix requires Lambda replacement with brief outage. Risk outweighs benefit unless doing major infra work anyway. |

**Recommendation**: Live with current naming. If we ever do a major infrastructure change that touches prod Lambda, rename it then.

### Keep Open - Reframe Scope (1 issue)

| Issue | Title | Reason |
|-------|-------|--------|
| #229 | Epic: eliminate enable_* divergence | Has caused real deployment failures (staging worked, prod didn't). |

**Reframe**: Don't pursue full tfvars parity. Instead:

1. Document known divergences and why they exist
2. Add comments in tfvars explaining which flags are intentionally different
3. Consider adding CI check that warns when staging PR might behave differently in prod

This is lower effort than full remediation and addresses the actual problem (unexpected behavior).

## Cost Analysis

Current infrastructure costs are reasonable for the value delivered:

| Environment | Monthly Cost | Notes |
|-------------|--------------|-------|
| Production | ~$46 | Aurora, CloudFront, Lambda, WAF |
| Staging | ~$14 | db.t3.micro, minimal NAT usage |
| **Total** | **~$60** | Well-optimized serverless architecture |

The proposed "cost saving" issues (#477, #476) claimed ~$80/mo savings but actual analysis shows:

- Staging RDS is already the smallest instance class
- NAT Gateway is already disabled in production
- Staging NAT costs are proportional to actual usage (scales to near-zero when idle)

## Strategic Direction

Focus infrastructure effort on:

1. **Bedrock/AI features** - This is where product value comes from
2. **Operational stability** - Keep deploys working, don't add complexity
3. **Documentation** - Better docs over more automation

Avoid:

- Premature optimization for costs that aren't material
- Infrastructure features for product features that may be cut
- "Consistency" work that doesn't solve real problems

## Appendix: AWS Well-Architected Assessment

### Operational Excellence

- **Current**: Good - Terraform IaC, CI/CD, health checks
- **Gap**: Documentation of staging/prod differences (addressed by #229 reframe)

### Security

- **Current**: Strong - IAM least privilege, VPC isolation, encryption at rest
- **Gap**: None identified

### Reliability

- **Current**: Adequate for scale - Multi-AZ RDS, S3 versioning, DLQs
- **Gap**: None material for current traffic levels

### Performance Efficiency

- **Current**: Good - Serverless auto-scaling, CloudFront CDN, appropriate Lambda sizing
- **Gap**: None identified

### Cost Optimization

- **Current**: Well-optimized - Scales to zero, no over-provisioning
- **Gap**: None material - proposed savings don't justify effort

### Sustainability

- **Current**: Serverless = efficient resource utilization
- **Gap**: None identified
