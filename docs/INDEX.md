# BlueMoxon Documentation

Start here to find what you need.

## Quick Start

| Guide | Purpose |
|-------|---------|
| [Development Setup](DEVELOPMENT.md) | Local environment setup |
| [Architecture Overview](ARCHITECTURE.md) | System design and components |
| [Features Catalog](FEATURES.md) | What the system does |

## For Operations

| Document | Purpose |
|----------|---------|
| [Operations Runbook](OPERATIONS.md) | Health checks, migrations, troubleshooting |
| [Deployment Guide](DEPLOYMENT.md) | Deploy procedures |
| [Rollback Procedures](ROLLBACK.md) | Rollback Lambda, S3, database |
| [Database Sync](DATABASE_SYNC.md) | Prod → Staging data sync |
| [CI/CD Pipeline](CI_CD.md) | GitHub Actions workflows |
| [Infrastructure](INFRASTRUCTURE.md) | AWS resources and Terraform |

## For Developers

| Document | Purpose |
|----------|---------|
| [API Reference](API_REFERENCE.md) | Endpoint documentation |
| [Database Schema](DATABASE.md) | Tables, indexes, migrations |
| [Data Migration](MIGRATION.md) | Legacy data import scripts |
| [Bedrock Integration](BEDROCK.md) | Claude AI analysis |
| [Performance](PERFORMANCE.md) | Core Web Vitals, optimization |
| [Infrastructure](INFRASTRUCTURE.md) | AWS resources and Terraform |

## Reference

| Document | Purpose |
|----------|---------|
| [CLAUDE.md](../CLAUDE.md) | AI assistant quick reference |
| [Prompting Guide](PROMPTING_GUIDE.md) | Session handoff templates |
| [Roadmap](ROADMAP.md) | Future development plans |

## Infrastructure Modules

Terraform modules in `infra/terraform/modules/`:

| Module | Purpose |
|--------|---------|
| [api-gateway](../infra/terraform/modules/api-gateway/README.md) | HTTP API + custom domain |
| [cloudfront](../infra/terraform/modules/cloudfront/README.md) | CDN distributions |
| [cognito](../infra/terraform/modules/cognito/README.md) | User authentication |
| [lambda](../infra/terraform/modules/lambda/README.md) | API function + IAM |
| [rds](../infra/terraform/modules/rds/README.md) | Aurora Serverless v2 |
| [s3](../infra/terraform/modules/s3/README.md) | Storage buckets |
| [vpc-networking](../infra/terraform/modules/vpc-networking/README.md) | VPC endpoints, NAT |

## Session Documentation

Active work sessions with artifacts:

- [2025-12-21 Documentation Review](session-2025-12-21-documentation-review/README.md) - This review

## Quick Links

**Staging Environment:**
- Frontend: https://staging.app.bluemoxon.com
- API: https://staging.api.bluemoxon.com
- Health: https://staging.api.bluemoxon.com/api/v1/health/deep

**Production:**
- Frontend: https://app.bluemoxon.com
- API: https://api.bluemoxon.com
