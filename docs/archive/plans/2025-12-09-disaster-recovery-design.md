# Disaster Recovery Design

**Date:** 2025-12-09
**Status:** Approved

## Overview

Snapshot-based disaster recovery for bluemoxon production environment. Focused on protecting against accidental deletion and data corruption with minimal infrastructure overhead.

## Requirements

| Requirement | Target |
|-------------|--------|
| Recovery Time Objective (RTO) | < 24 hours |
| Recovery Point Objective (RPO) | Up to 24 hours |
| Scenarios covered | Accidental deletion, bad deploys, data corruption |
| Out of scope | Multi-region failover, real-time replication |

## Current State & Gaps

| Resource | Current DR Capability | Gap |
|----------|----------------------|-----|
| **RDS (PostgreSQL)** | 7-day automated backups, daily snapshots at 03:00 UTC, deletion protection, final snapshot on delete | No documented restore procedure |
| **S3 Images Bucket** | Versioning enabled - can recover deleted/overwritten objects | No documented recovery procedure |
| **S3 Frontend Bucket** | No versioning - if deleted, must redeploy | Enable versioning |
| **Lambda/API Gateway** | Stateless, rebuilt from code | None - redeploy from git |
| **Cognito** | User pool data managed by AWS | Acceptable risk for small user base |
| **CloudFront** | Configuration in Terraform | None - recreate from IaC |

## RDS Recovery Procedures

### Automated Backups (already configured)

- Daily snapshots at 03:00-04:00 UTC
- 7-day retention
- Stored in us-west-2

### Scenario 1: Restore entire database from snapshot

When to use: Database corruption, catastrophic data loss, need to roll back to previous day.

```bash
# 1. List available snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier bluemoxon-db \
  --query 'DBSnapshots[*].[DBSnapshotIdentifier,SnapshotCreateTime]' \
  --output table

# 2. Restore to new instance (takes 10-30 min)
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier bluemoxon-db-restored \
  --db-snapshot-identifier <snapshot-id> \
  --db-subnet-group-name bluemoxon-db-subnet-group \
  --vpc-security-group-ids <sg-id>

# 3. Update application to point to new instance
#    (update Secrets Manager or Lambda env vars)

# 4. Verify, then delete old instance if desired
```

### Scenario 2: Manual snapshot before risky operations

When to use: Before migrations, bulk data changes, major deploys.

```bash
aws rds create-db-snapshot \
  --db-instance-identifier bluemoxon-db \
  --db-snapshot-identifier pre-migration-$(date +%Y%m%d-%H%M)
```

## S3 Recovery Procedures

### Images Bucket (versioning enabled)

**Recover deleted object:**

```bash
# List versions including delete markers
aws s3api list-object-versions \
  --bucket bluemoxon-images \
  --prefix "path/to/object" \
  --query 'Versions[*].[Key,VersionId,IsLatest,LastModified]'

# Restore by copying previous version to current
aws s3api copy-object \
  --bucket bluemoxon-images \
  --key "path/to/object" \
  --copy-source "bluemoxon-images/path/to/object?versionId=<version-id>"
```

**Recover overwritten object:** Same as above - previous versions are retained.

### Frontend Bucket

**If objects deleted:** Redeploy from CI/CD.

```bash
gh workflow run deploy.yml
# Or manually:
cd frontend && npm run build
aws s3 sync dist/ s3://bluemoxon-frontend/
```

## Validation & Maintenance

### Periodic Validation (quarterly)

1. **RDS restore test:**
   - Restore latest snapshot to a temporary instance
   - Verify data integrity with a few queries
   - Delete temporary instance
   - Document: date tested, snapshot used, any issues

2. **S3 version recovery test:**
   - Upload a test file, overwrite it, delete it
   - Recover each version
   - Verify contents match expected

### When to Take Manual Snapshots

- Before Alembic migrations
- Before bulk data operations (imports, deletes)
- Before major deployments affecting data
- Before Terraform changes to RDS

### Retention Policy

| Snapshot Type | Retention |
|---------------|-----------|
| Automated daily | 7 days (AWS managed) |
| Pre-migration manual | 30 days, then delete |
| Pre-major-release | Keep until next major release |

### Cost

Manual RDS snapshots cost ~$0.02/GB/month. At 20GB, that's ~$0.40/month per snapshot.

## Implementation Checklist

**Immediate actions (one-time):**

- [ ] Enable versioning on frontend S3 bucket (Terraform change)
- [ ] Verify current RDS backup settings in AWS console match expectations

**Ongoing practices:**

- [ ] Take manual snapshot before migrations/major changes
- [ ] Quarterly: Test RDS restore to temporary instance
- [ ] Quarterly: Test S3 version recovery
- [ ] Periodically: Clean up old manual snapshots (>30 days)

## No Changes Needed

These are already properly configured:

- RDS automated backups (7-day retention)
- S3 images versioning (enabled)
- Deletion protection on RDS (enabled)
- Final snapshot on RDS deletion (configured)
