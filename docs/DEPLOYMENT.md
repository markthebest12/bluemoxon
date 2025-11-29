# Deployment Guide

## Prerequisites

- AWS CLI configured with appropriate credentials
- AWS CDK CLI installed (`npm install -g aws-cdk`)
- Python 3.11+ with Poetry
- Domain name ready (bluemoxon.com or similar)

## Initial AWS Setup

### Bootstrap CDK

```bash
cd infra
poetry install

# Bootstrap CDK in your account/region
cdk bootstrap aws://ACCOUNT_ID/us-east-1
```

### Deploy Infrastructure

Deploy in order (dependencies):

```bash
# Deploy all stacks
cdk deploy --all

# Or deploy individually in order:
cdk deploy BlueMoxonNetworkStack
cdk deploy BlueMoxonDatabaseStack
cdk deploy BlueMoxonAuthStack
cdk deploy BlueMoxonStorageStack
cdk deploy BlueMoxonApiStack
cdk deploy BlueMoxonFrontendStack
cdk deploy BlueMoxonDnsStack
cdk deploy BlueMoxonPipelineStack
```

## Stack Details

### NetworkStack
Creates VPC with:
- 2 Availability Zones
- Public subnets (NAT Gateway)
- Private isolated subnets (for Aurora)

### DatabaseStack
Creates:
- Aurora Serverless v2 PostgreSQL 15
- Min 0.5 ACU, Max 2 ACU
- Secrets Manager for credentials
- Security group (Lambda access only)

### AuthStack
Creates:
- Cognito User Pool
- MFA required (TOTP)
- No self-signup
- App client for frontend

### StorageStack
Creates:
- S3 bucket for frontend assets
- S3 bucket for book images
- Bucket policies and CORS

### ApiStack
Creates:
- Lambda function (Python 3.11)
- API Gateway HTTP API
- VPC connectivity
- Environment variables from Secrets Manager

### FrontendStack
Creates:
- CloudFront distribution
- S3 origin with OAI
- Custom error responses (SPA routing)

### DnsStack
Creates:
- Route 53 hosted zone
- ACM certificate (us-east-1)
- A/AAAA records for CloudFront

### PipelineStack
Creates:
- CodePipeline
- GitHub source connection
- CodeBuild projects
- Manual approval stage

## Post-Deployment

### Run Migrations

```bash
# Get database connection from Secrets Manager
aws secretsmanager get-secret-value --secret-id bluemoxon/db

# Connect and run migrations
cd backend
DATABASE_URL=<from-secret> alembic upgrade head
```

### Create Admin User

```bash
# Using AWS CLI
aws cognito-idp admin-create-user \
  --user-pool-id <pool-id> \
  --username admin@example.com \
  --user-attributes Name=email,Value=admin@example.com \
  --temporary-password TempPass123!

# Or using invite script
python scripts/invite_user.py --email admin@example.com --role admin
```

### Seed Reference Data

```bash
python scripts/seed_data.py --env production
```

### Initial Data Migration

```bash
python scripts/sync_from_legacy.py \
  --source ~/projects/book-collection \
  --apply \
  --env production
```

## CI/CD Pipeline

### Trigger
Push to `main` branch triggers the pipeline.

### Stages
1. **Source:** GitHub webhook
2. **Build:**
   - Frontend: npm build
   - Backend: Poetry install, pytest
   - CDK: cdk synth
3. **Manual Approval:** SNS notification
4. **Deploy:**
   - CDK deploy
   - S3 sync
   - CloudFront invalidation

### Manual Deployment

```bash
# Deploy backend
cd backend
./deploy.sh

# Deploy frontend
cd frontend
npm run build
aws s3 sync dist/ s3://bluemoxon-frontend/
aws cloudfront create-invalidation --distribution-id <id> --paths "/*"
```

## Monitoring

### CloudWatch
- Lambda logs: `/aws/lambda/bluemoxon-api`
- API Gateway logs: Enabled on API
- Aurora logs: PostgreSQL logs

### Alarms (Recommended)
- Lambda errors > 5 in 5 minutes
- Aurora CPU > 80%
- API Gateway 5xx > 10 in 5 minutes

## Costs

Monitor via AWS Cost Explorer. Expected: $27-49/month

Major cost drivers:
- Aurora Serverless v2: ~$15-25
- NAT Gateway: ~$5-10
- CloudFront: ~$2-5
