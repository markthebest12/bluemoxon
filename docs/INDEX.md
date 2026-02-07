# BlueMoxon Documentation

Start here to find what you need.

## What's New in BMX 3.0

- **Social Circles** -- Interactive network graph showing who knew whom across the collection
- **Entity Profiles** -- AI-generated bios, stories, and connection narratives for authors, publishers, and binders
- **AI-Discovered Connections** -- Personal connections (family, friendship, influence, collaboration, scandal) via Bedrock
- **Model Registry** -- Admin-configurable AI model selection per workflow

See [Features](FEATURES.md#whats-new-in-bmx-30--social-circles) for full details.

## Quick Start

| Guide | Purpose |
|-------|---------|
| [Development Setup](DEVELOPMENT.md) | Local environment setup |
| [Architecture Overview](ARCHITECTURE.md) | System design and components |
| [Features Catalog](FEATURES.md) | What the system does |

## For Operations

| Document | Purpose |
|----------|---------|
| [Admin Dashboard](ADMIN_DASHBOARD.md) | System monitoring, config, cost tracking |
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

Terraform modules in `infra/terraform/modules/` (23 modules):

| Module | Purpose |
|--------|---------|
| [analysis-worker](../infra/terraform/modules/analysis-worker/) | Napoleon analysis Lambda |
| [api-gateway](../infra/terraform/modules/api-gateway/) | HTTP API + custom domain |
| [cleanup-lambda](../infra/terraform/modules/cleanup-lambda/) | Orphan resource cleanup |
| [cloudfront](../infra/terraform/modules/cloudfront/) | CDN distributions |
| [cognito](../infra/terraform/modules/cognito/) | User authentication |
| [db-sync-lambda](../infra/terraform/modules/db-sync-lambda/) | Prod-to-staging data sync |
| [dns](../infra/terraform/modules/dns/) | Route 53 DNS records |
| [elasticache](../infra/terraform/modules/elasticache/) | Redis caching |
| [eval-runbook-worker](../infra/terraform/modules/eval-runbook-worker/) | Eval runbook generation |
| [github-oidc](../infra/terraform/modules/github-oidc/) | GitHub Actions OIDC auth |
| [image-processor](../infra/terraform/modules/image-processor/) | AI image processing Lambda |
| [lambda](../infra/terraform/modules/lambda/) | API function + IAM |
| [lambda-layer](../infra/terraform/modules/lambda-layer/) | Shared Python dependencies |
| [landing-site](../infra/terraform/modules/landing-site/) | Marketing site hosting |
| [notifications](../infra/terraform/modules/notifications/) | SNS notifications |
| [profile-worker](../infra/terraform/modules/profile-worker/) | Entity profile generation |
| [rds](../infra/terraform/modules/rds/) | Aurora Serverless v2 |
| [retry-queue-failed-worker](../infra/terraform/modules/retry-queue-failed-worker/) | Failed job retry |
| [s3](../infra/terraform/modules/s3/) | Storage buckets |
| [scraper-lambda](../infra/terraform/modules/scraper-lambda/) | eBay scraper (Docker) |
| [secrets](../infra/terraform/modules/secrets/) | Secrets Manager |
| [tracking-worker](../infra/terraform/modules/tracking-worker/) | Shipment tracking |
| [vpc-networking](../infra/terraform/modules/vpc-networking/) | VPC endpoints, NAT |

## Quick Links

**Staging Environment:**

- Frontend: <https://staging.app.bluemoxon.com>
- API: <https://staging.api.bluemoxon.com>
- Health: <https://staging.api.bluemoxon.com/api/v1/health/deep>

**Production:**

- Frontend: <https://app.bluemoxon.com>
- API: <https://api.bluemoxon.com>
