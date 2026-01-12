# Database Sync: Production to Staging

This document describes how to sync the production database to the staging environment.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AWS Account: Production                          │
│  ┌─────────────────────┐         ┌──────────────────────────────────┐   │
│  │   Secrets Manager   │         │         Aurora PostgreSQL        │   │
│  │ bluemoxon/db-creds  │         │  bluemoxon-cluster               │   │
│  └─────────────────────┘         │  VPC: 10.0.0.0/16                │   │
│                                  └──────────────────────────────────┘   │
└─────────────────────────────────────────│───────────────────────────────┘
                                          │
                                    VPC Peering
                                  pcx-02121caf322533640
                                          │
┌─────────────────────────────────────────│───────────────────────────────┐
│                          AWS Account: Staging                            │
│                                         │                                │
│  ┌─────────────────────┐         ┌──────▼───────────────────────────┐   │
│  │   Secrets Manager   │         │         RDS PostgreSQL           │   │
│  │ bluemoxon-staging/  │         │  bluemoxon-staging-db            │   │
│  │ database            │         │  VPC: 172.31.0.0/16              │   │
│  └─────────────────────┘         └──────────────────────────────────┘   │
│                                         ▲                                │
│  ┌──────────────────────────────────────┴───────────────────────────┐   │
│  │                    Lambda: bluemoxon-staging-db-sync             │   │
│  │  - Runs in staging VPC                                            │   │
│  │  - Reads from prod Aurora via VPC peering                         │   │
│  │  - Writes to staging RDS                                          │   │
│  │  - 15 minute timeout                                              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **VPC Peering**: Already configured between prod and staging VPCs
   - Peering ID: `pcx-02121caf322533640`
   - Routes configured in both VPCs
   - Security groups allow PostgreSQL (5432) traffic

2. **VPC Endpoint for Secrets Manager**: Required for Lambda to access Secrets Manager from within VPC
   - Endpoint ID: `vpce-090b1d2f90e8e19cf`
   - Security group must allow HTTPS (443) from Lambda security group

3. **Secrets Manager**: Database credentials stored in staging account
   - Staging: `bluemoxon-staging/database`
   - Prod credentials: Passed via environment variables (due to cross-account KMS limitations)

4. **Lambda Function**: `bluemoxon-staging-db-sync` deployed in staging VPC

## Sync Methods

### Method 1: Lambda Function (Recommended)

The sync Lambda runs entirely within AWS, no local access required.

**Full database sync (requires prod DB credentials):**
```bash
aws lambda invoke \
    --function-name bluemoxon-staging-db-sync \
    --profile staging \
    --payload '{}' \
    .tmp/sync-response.json

# Check results
cat .tmp/sync-response.json | jq
```

**Cognito mapping only (no DB sync, no prod credentials needed):**
```bash
# Maps staging Cognito user subs to database users by email
aws lambda invoke \
    --function-name bluemoxon-staging-db-sync \
    --profile staging \
    --payload '{"cognito_only": true}' \
    --cli-binary-format raw-in-base64-out \
    .tmp/cognito-sync.json

cat .tmp/cognito-sync.json | jq
```

This is useful after creating new users in staging Cognito to update the `cognito_sub` column in the users table.

**Monitor progress:**
```bash
# Watch CloudWatch logs
aws logs tail /aws/lambda/bluemoxon-staging-db-sync \
    --profile staging \
    --follow
```

### Method 2: Shell Script (Requires VPC Access)

If you have network access to both databases (e.g., from a bastion host):

```bash
./scripts/sync-prod-to-staging.sh --db-only --yes
```

## Lambda Deployment

### Initial Deployment (First Time)

```bash
# Requires Docker for building Lambda package
./scripts/deploy-db-sync-lambda.sh --create
```

This creates:
- IAM role with Secrets Manager access
- Lambda function in staging VPC
- Environment variables configured

### Update Lambda Code

```bash
./scripts/deploy-db-sync-lambda.sh --update
```

## How the Sync Works

1. **Connect**: Lambda connects to both databases using credentials
2. **List Tables**: Gets all tables from production `public` schema
3. **Disable FK Checks**: Temporarily disables foreign key constraints in staging
4. **For Each Table**:
   - **Create table if missing**: Automatically creates table in staging if it doesn't exist
   - Truncate staging table (CASCADE)
   - Copy all rows from production
5. **Re-enable FK Checks**: Restores foreign key constraints
6. **Flush Redis Cache**: Clears staging ElastiCache to prevent stale dashboard data
7. **Report**: Returns summary of tables created, synced, and row counts

### Redis Cache Flush

After syncing the database, the staging Redis cache must be flushed to prevent stale dashboard statistics. The sync script automatically flushes Redis when the `REDIS_HOST` environment variable is set.

**Why this matters:** Dashboard stats are cached for 5 minutes. Without flushing, the staging dashboard would show production metrics for up to 5 minutes after sync.

**Manual flush (if needed):**
```bash
# Connect to staging Redis via Lambda
aws lambda invoke \
    --function-name bluemoxon-staging-api \
    --profile bmx-staging \
    --payload '{"path": "/api/v1/admin/cache/flush", "httpMethod": "POST"}' \
    .tmp/flush-response.json
```

**Note:** The sync Lambda can initialize an empty staging database by creating tables automatically.
This eliminates the need to run Alembic migrations separately.

## Configuration

### Lambda Environment Variables

| Variable | Description |
|----------|-------------|
| `STAGING_SECRET_ARN` | ARN of staging database secret (required) |
| `PROD_DB_HOST` | Production database hostname |
| `PROD_DB_USER` | Production database username |
| `PROD_DB_PASSWORD` | Production database password |
| `PROD_DB_NAME` | Production database name (default: bluemoxon) |
| `PROD_DB_PORT` | Production database port (default: 5432) |

**Note:** Production credentials are passed directly due to cross-account KMS limitations.
The sync Lambda cannot access prod secrets encrypted with the default KMS key.

### Lambda Settings

| Setting | Value |
|---------|-------|
| Runtime | Python 3.12 |
| Timeout | 15 minutes (900 seconds) |
| Memory | 512 MB |
| VPC | Staging VPC (vpc-03f78def84c9e85e0) |

## Troubleshooting

### Lambda Times Out

The default timeout is 15 minutes. For very large databases:
1. Increase Lambda timeout (max 15 min)
2. Consider syncing tables in batches
3. Use pg_dump/pg_restore via EC2 for huge datasets

### Connection Errors

**"Connection refused" to production:**
- Check VPC peering status: `aws ec2 describe-vpc-peering-connections`
- Verify route tables have peering routes
- Check security group allows 5432 from staging CIDR

**"Connection refused" to staging:**
- Lambda must be in same VPC as RDS
- Check security group allows Lambda's security group

### Secrets Manager Errors

**"Access Denied":**
- Lambda role needs `secretsmanager:GetSecretValue` permission
- For cross-account (prod secret), the secret must have a resource policy allowing staging account

**Cross-Account Secret Access:**
If Lambda can't access prod secret, add resource policy to prod secret:
```bash
aws secretsmanager put-resource-policy \
    --secret-id bluemoxon/db-credentials \
    --resource-policy '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::652617421195:root"},
            "Action": "secretsmanager:GetSecretValue",
            "Resource": "*"
        }]
    }'
```

## Security Considerations

1. **No public database access**: Both databases are private, only accessible within VPCs
2. **Credentials in Secrets Manager**: No hardcoded passwords
3. **VPC peering**: Traffic stays within AWS network
4. **IAM least privilege**: Lambda only has required permissions

## Related Files

- Lambda code: `backend/lambdas/db_sync/handler.py`
- Deploy script: `scripts/deploy-db-sync-lambda.sh`
- Shell sync script: `scripts/sync-prod-to-staging.sh`
- VPC peering issue: #105
