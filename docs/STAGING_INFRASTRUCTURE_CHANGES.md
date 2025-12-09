# Staging Infrastructure Changes - 2025-12-07

## Summary

Manual changes made to fix staging environment issues. These need to be captured in Terraform.

## Changes Made

### 1. Deleted Cognito VPC Endpoint

**Problem**: PrivateLink access disabled error when using Managed Login + VPC endpoint
**Fix**: Deleted VPC endpoint `vpce-0256de046ef7a09f4`
**Command**:
```bash
AWS_PROFILE=staging aws ec2 delete-vpc-endpoints --vpc-endpoint-ids vpce-0256de046ef7a09f4
```

### 2. Created NAT Gateway

**Problem**: Lambda in VPC needs internet access to reach Cognito APIs
**Fix**: Created NAT Gateway like prod has

| Resource | ID |
|----------|-----|
| Elastic IP | `eipalloc-0b4dc0b1aba0c7b27` |
| NAT Gateway | `nat-0976b52974205934f` |
| Subnet (public, for NAT) | `subnet-0c5f84e98ba25334d` (us-west-2a) |

### 3. Created Private Route Table

**Problem**: Lambda subnets need to route through NAT Gateway
**Fix**: Created private route table with NAT route

| Resource | ID |
|----------|-----|
| Route Table | `rtb-00c330cfe9829abc4` |
| Route | 0.0.0.0/0 -> `nat-0976b52974205934f` |

**Associated Subnets** (private, for Lambda):
- `subnet-0ceb0276fa36428f2` (us-west-2b)
- `subnet-09eeb023cb49a83d5` (us-west-2c)
- `subnet-0bfb299044084bad3` (us-west-2d)

### 4. Updated Lambda VPC Configuration

**Fix**: Removed Lambda from public subnet (us-west-2a), keep only in private subnets
**Command**:
```bash
AWS_PROFILE=staging aws lambda update-function-configuration \
  --function-name bluemoxon-staging-api \
  --vpc-config SubnetIds=subnet-0ceb0276fa36428f2,subnet-09eeb023cb49a83d5,subnet-0bfb299044084bad3,SecurityGroupIds=sg-050fb5268bcd06443
```

### 5. Added Cognito IAM Permissions to Lambda Role

**Problem**: Lambda role `bluemoxon-staging-api-exec-role` lacked Cognito permissions
**Fix**: Added inline policy `cognito-access`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cognito-idp:Admin*",
        "cognito-idp:Describe*",
        "cognito-idp:Get*",
        "cognito-idp:List*"
      ],
      "Resource": "arn:aws:cognito-idp:us-west-2:652617421195:userpool/us-west-2_5pOhFH6LN"
    }
  ]
}
```

### 6. Enabled MFA on Cognito Pool

**Fix**: Set MFA to OPTIONAL with TOTP enabled (matches prod)
**Command**:
```bash
AWS_PROFILE=staging aws cognito-idp set-user-pool-mfa-config \
  --user-pool-id us-west-2_5pOhFH6LN \
  --mfa-configuration OPTIONAL \
  --software-token-mfa-configuration Enabled=true
```

### 8. Added Keep-Warm EventBridge Rule

**Problem**: Lambda cold starts take ~4 seconds, causing 503 timeouts on first request after idle
**Fix**: Created EventBridge rule to ping Lambda every 5 minutes

| Resource | ID/ARN |
|----------|--------|
| Rule | `bluemoxon-staging-keep-warm` |
| Rule ARN | `arn:aws:events:us-west-2:652617421195:rule/bluemoxon-staging-keep-warm` |

**Commands**:
```bash
AWS_PROFILE=staging aws events put-rule --name bluemoxon-staging-keep-warm --schedule-expression "rate(5 minutes)" --state ENABLED

AWS_PROFILE=staging aws lambda add-permission --function-name bluemoxon-staging-api --statement-id keep-warm-event --action lambda:InvokeFunction --principal events.amazonaws.com --source-arn arn:aws:events:us-west-2:652617421195:rule/bluemoxon-staging-keep-warm

AWS_PROFILE=staging aws events put-targets --rule bluemoxon-staging-keep-warm --targets '[{"Id":"1","Arn":"arn:aws:lambda:us-west-2:652617421195:function:bluemoxon-staging-api"}]'
```

### 7. Fixed API Gateway CORS (earlier session)

**Fix**: Updated CORS to include correct origin
**Config**:
```json
{
  "AllowCredentials": true,
  "AllowHeaders": ["*"],
  "AllowMethods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
  "AllowOrigins": ["https://staging.app.bluemoxon.com", "http://localhost:5173"],
  "ExposeHeaders": ["x-environment", "x-app-version"],
  "MaxAge": 3600
}
```

## Current Status

**Working**:
- Login flow
- Admin page (users list, roles, MFA status)
- API endpoints (books, etc.)
- CORS properly configured
- Cognito IAM permissions
- MFA enabled at pool level (OPTIONAL with TOTP)
- MFA status display per user
- "Enable MFA" button for users

**Known Issues**:
- Other users show "User does not exist" (expected - exist in DB from prod sync but not in staging Cognito)

## Remaining Terraform Work

All above changes need to be added to Terraform modules:

1. **VPC Module**: Add NAT Gateway, private route table, subnet associations
2. **Lambda Module**: Update VPC config to use only private subnets
3. **IAM Module**: Add Cognito permissions to Lambda execution role
4. **Cognito Module**: Set MFA configuration to OPTIONAL with TOTP

## Key Differences: Staging vs Prod

| Component | Production | Staging |
|-----------|------------|---------|
| NAT Gateway | `nat-0551444ab65c31f8c` | `nat-0976b52974205934f` |
| Cognito VPC Endpoint | None | None (deleted) |
| MFA | OPTIONAL | OPTIONAL |
| Cognito Pool | `us-west-2_PvdIpXVKF` | `us-west-2_5pOhFH6LN` |

## Staging AWS Resource IDs

| Resource | ID |
|----------|-----|
| VPC | `vpc-03f78def84c9e85e0` (default VPC) |
| Lambda | `bluemoxon-staging-api` |
| Lambda Exec Role | `bluemoxon-staging-api-exec-role` |
| API Gateway | `ikxdby8a89` |
| Cognito Pool | `us-west-2_5pOhFH6LN` |
| Cognito Client | `48ik81mrpc6anouk234sq31fbt` |
| Cognito Domain | `bluemoxon-staging` |
| NAT Gateway | `nat-0976b52974205934f` |
| Elastic IP | `eipalloc-0b4dc0b1aba0c7b27` |
| Private Route Table | `rtb-00c330cfe9829abc4` |
| Public Subnet | `subnet-0c5f84e98ba25334d` (us-west-2a) |
| Private Subnets | `subnet-0ceb0276fa36428f2`, `subnet-09eeb023cb49a83d5`, `subnet-0bfb299044084bad3` |
| Lambda Security Group | `sg-050fb5268bcd06443` |

## Estimated Monthly Cost Impact

| Resource | Cost |
|----------|------|
| NAT Gateway | ~$32/month |
| Elastic IP | ~$3.65/month (if unattached) |

Total staging cost increase: ~$32/month (NAT Gateway was missing from original plan)
