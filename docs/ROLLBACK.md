# BlueMoxon Rollback Procedures

Quick reference for rolling back deployments when issues occur.

---

## Table of Contents

1. [Lambda Rollback](#lambda-rollback)
2. [Frontend (S3) Rollback](#frontend-s3-rollback)
3. [Database Rollback](#database-rollback)
4. [Full Rollback Checklist](#full-rollback-checklist)

---

## Lambda Rollback

Lambda uses versioning with a `prod` alias. Rollback by pointing the alias to a previous version.

### View Available Versions

```bash
# List all Lambda versions
aws lambda list-versions-by-function \
  --profile bluemoxon \
  --region us-west-2 \
  --function-name bluemoxon-api \
  --query 'Versions[*].[Version,Description,LastModified]' \
  --output table
```

### Check Current Alias

```bash
# See what version prod alias points to
aws lambda get-alias \
  --profile bluemoxon \
  --region us-west-2 \
  --function-name bluemoxon-api \
  --name prod
```

### Rollback to Previous Version

```bash
# Replace VERSION_NUMBER with the version to rollback to (e.g., 5)
aws lambda update-alias \
  --profile bluemoxon \
  --region us-west-2 \
  --function-name bluemoxon-api \
  --name prod \
  --function-version VERSION_NUMBER
```

### Verify Rollback

```bash
# Test API health
curl -s https://api.bluemoxon.com/health | jq

# Test books endpoint
curl -s "https://api.bluemoxon.com/api/v1/books?per_page=1" | jq
```

---

## Frontend (S3) Rollback

S3 versioning is enabled. Rollback by restoring previous versions of files.

### View Previous Versions of index.html

```bash
aws s3api list-object-versions \
  --profile bluemoxon \
  --region us-west-2 \
  --bucket bluemoxon-frontend \
  --prefix index.html \
  --query 'Versions[*].[VersionId,LastModified,IsLatest]' \
  --output table
```

### Restore Previous index.html Version

```bash
# Replace VERSION_ID with the version to restore
aws s3api copy-object \
  --profile bluemoxon \
  --region us-west-2 \
  --bucket bluemoxon-frontend \
  --copy-source "bluemoxon-frontend/index.html?versionId=VERSION_ID" \
  --key index.html \
  --cache-control "no-cache,no-store,must-revalidate"
```

### Quick Rollback Script (All Frontend Files)

For a full frontend rollback, redeploy from a previous git commit:

```bash
# 1. Find the commit to rollback to
git log --oneline -10

# 2. Checkout that commit
git checkout COMMIT_HASH -- frontend/

# 3. Rebuild and deploy
cd frontend
npm ci
npm run build

# 4. Sync to S3 (use deploy workflow or manual)
aws s3 sync dist/ s3://bluemoxon-frontend/ \
  --profile bluemoxon \
  --region us-west-2 \
  --delete \
  --cache-control "max-age=31536000,public" \
  --exclude "index.html" \
  --exclude "*.json"

aws s3 cp dist/index.html s3://bluemoxon-frontend/index.html \
  --profile bluemoxon \
  --region us-west-2 \
  --cache-control "no-cache,no-store,must-revalidate"
```

### Invalidate CloudFront Cache

After any S3 rollback, invalidate the cache:

```bash
aws cloudfront create-invalidation \
  --profile bluemoxon \
  --region us-west-2 \
  --distribution-id E16BJX90QWQNQO \
  --paths "/*"
```

---

## Database Rollback

Aurora Serverless v2 has automated daily backups with 7-day retention.

### View Available Snapshots

```bash
# List automated snapshots
aws rds describe-db-cluster-snapshots \
  --profile bluemoxon \
  --region us-west-2 \
  --db-cluster-identifier bluemoxon-db \
  --snapshot-type automated \
  --query 'DBClusterSnapshots[*].[DBClusterSnapshotIdentifier,SnapshotCreateTime]' \
  --output table
```

### Create Manual Snapshot Before Risky Changes

```bash
aws rds create-db-cluster-snapshot \
  --profile bluemoxon \
  --region us-west-2 \
  --db-cluster-identifier bluemoxon-db \
  --db-cluster-snapshot-identifier "pre-deploy-$(date +%Y%m%d-%H%M)"
```

### Point-in-Time Recovery

Aurora supports point-in-time recovery to any second in the retention period:

```bash
# Restore to a new cluster (then swap)
aws rds restore-db-cluster-to-point-in-time \
  --profile bluemoxon \
  --region us-west-2 \
  --source-db-cluster-identifier bluemoxon-db \
  --db-cluster-identifier bluemoxon-db-restored \
  --restore-to-time "2025-01-15T10:00:00Z" \
  --vpc-security-group-ids sg-XXXXX \
  --db-subnet-group-name bluemoxon-db-subnet
```

**Note:** Database rollback is disruptive. For minor issues, prefer fixing forward.

---

## Full Rollback Checklist

When a deployment causes issues:

### 1. Identify the Problem

- [ ] Check CloudWatch logs for Lambda errors
- [ ] Check browser console for frontend errors
- [ ] Verify API health: `curl https://api.bluemoxon.com/health`
- [ ] Verify frontend loads: `curl https://bluemoxon.com`

### 2. Determine Scope

- [ ] Is it a backend (Lambda) issue? → Lambda rollback
- [ ] Is it a frontend issue? → S3 rollback
- [ ] Is it a data issue? → Consider database rollback (last resort)

### 3. Execute Rollback

For Lambda:
```bash
# Get previous version number
aws lambda list-versions-by-function \
  --profile bluemoxon \
  --region us-west-2 \
  --function-name bluemoxon-api \
  --query 'Versions[-2].Version' \
  --output text

# Update alias to previous version
aws lambda update-alias \
  --profile bluemoxon \
  --region us-west-2 \
  --function-name bluemoxon-api \
  --name prod \
  --function-version PREVIOUS_VERSION
```

For Frontend:
```bash
# Redeploy from previous git commit
git checkout HEAD~1 -- frontend/
cd frontend && npm ci && npm run build
# Then sync to S3 (see above)
```

### 4. Verify Fix

- [ ] API health returns 200
- [ ] Books endpoint returns data
- [ ] Frontend loads and displays books
- [ ] Images load correctly

### 5. Post-Rollback

- [ ] Document what went wrong
- [ ] Create fix in a new branch
- [ ] Test fix locally
- [ ] Deploy fix through normal CI/CD

---

## Version Retention Policies

| Component | Retention | Auto-Cleanup |
|-----------|-----------|--------------|
| Lambda versions | Last 3 | Yes (deploy workflow) |
| S3 versions | 30 days | Yes (lifecycle rule) |
| DB snapshots | 7 days | Yes (Aurora automated) |

---

## Useful Commands Reference

```bash
# Lambda: Get current prod version
aws lambda get-alias --profile bluemoxon --region us-west-2 \
  --function-name bluemoxon-api --name prod \
  --query 'FunctionVersion' --output text

# S3: List all versioned objects
aws s3api list-object-versions --profile bluemoxon --region us-west-2 \
  --bucket bluemoxon-frontend --max-items 20

# CloudFront: Check invalidation status
aws cloudfront get-invalidation --profile bluemoxon --region us-west-2 \
  --distribution-id E16BJX90QWQNQO --id INVALIDATION_ID

# CloudWatch: Tail Lambda logs
aws logs tail /aws/lambda/bluemoxon-api --profile bluemoxon --region us-west-2 --follow
```

---

**Last Updated:** 2025-11-30
