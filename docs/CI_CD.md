# CI/CD Pipeline

BlueMoxon uses GitHub Actions for continuous integration and deployment with a staging-first approach. The pipeline ensures code quality, security, and reliable deployments.

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GitHub Repository                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
┌───────▼───────┐          ┌────────▼────────┐         ┌────────▼────────┐
│ Pull Request  │          │ Push to staging │         │  Push to main   │
└───────┬───────┘          └────────┬────────┘         └────────┬────────┘
        │                           │                           │
┌───────▼───────┐          ┌────────▼────────┐         ┌────────▼────────┐
│  CI Workflow  │          │  CI Workflow    │         │  CI Workflow    │
│               │          │       +         │         │       +         │
│  • Lint       │          │  Deploy Staging │         │  Deploy Prod    │
│  • Test       │          │                 │         │                 │
│  • TypeCheck  │          │  • Build Lambda │         │  • Build Lambda │
│  • Security   │          │  • Build Frontend│        │  • Build Frontend│
│  • Build      │          │  • Upload to S3 │         │  • Upload to S3 │
└───────┬───────┘          │  • Smoke Tests  │         │  • Smoke Tests  │
        │                  └────────┬────────┘         │  • Create Tag   │
┌───────▼───────┐                   │                  └────────┬────────┘
│  PR Checks    │          ┌────────▼────────┐                  │
│    Pass       │          │    Staging      │         ┌────────▼────────┐
└───────────────┘          │   Environment   │         │   Production    │
                           └─────────────────┘         │   Environment   │
                                                       └─────────────────┘
```

## Workflows

### CI Workflow (`ci.yml`)

Runs on all pull requests to `staging` or `main`. Ensures code quality before merge.

**Jobs:**

| Job | Description | Blocking |
|-----|-------------|----------|
| `backend-lint` | Ruff linting and format check (incl. security rules) | Yes |
| `backend-test` | Pytest with PostgreSQL | Yes |
| `backend-typecheck` | Mypy type checking | No |
| `frontend-lint` | ESLint + Prettier | Yes |
| `frontend-typecheck` | Vue-tsc | Yes |
| `frontend-test` | Vitest | No |
| `frontend-build` | Production build | Yes |
| `sast-scan` | Bandit + Semgrep SAST analysis | **Yes** |
| `dependency-scan` | pip-audit + npm audit | **Yes** |
| `secret-scan` | Trivy + Gitleaks | **Yes** |

### Deploy Staging Workflow (`deploy-staging.yml`)

Runs on push to `staging` branch. Deploys to staging environment.

**Jobs:**

| Job | Description |
|-----|-------------|
| `ci` | Runs full CI workflow |
| `build-backend` | Creates Lambda deployment package |
| `build-frontend` | Builds Vue app with staging config |
| `deploy` | Uploads to S3, updates Lambda |
| `smoke-test` | Verifies staging API and frontend |

### Deploy Production Workflow (`deploy.yml`)

Runs on push to `main` branch. Deploys to production environment.

**Jobs:**

| Job | Description |
|-----|-------------|
| `ci` | Runs full CI workflow |
| `build-backend` | Creates Lambda deployment package |
| `build-frontend` | Builds Vue app with production config |
| `deploy` | Uploads to S3, updates Lambda, invalidates CloudFront |
| `smoke-test` | Verifies production API and frontend |
| `tag-release` | Creates version tag (YYYY.MM.DD-sha) |

### Deploy Site Workflow (`deploy-site.yml`)

Runs on push to `main` when `site/*` files change. Deploys marketing site.

| Job | Description |
|-----|-------------|
| `deploy-landing` | Uploads to S3, invalidates CloudFront |

### Terraform Workflow (`terraform.yml`)

Runs on PRs with `infra/terraform/**` changes. Plans infrastructure changes.

| Job | Description |
|-----|-------------|
| `plan` | Runs `terraform plan` on staging |

## Branch Strategy

```
main ─────●─────●─────●─────→  [Production: app.bluemoxon.com]
           \     \     \
staging ────●─────●─────●────→  [Staging: staging.app.bluemoxon.com]
             \   / \   /
feature ──────●     ●────────→  [Feature branches]
```

| Branch | Purpose | Protection | Deploy Target |
|--------|---------|------------|---------------|
| `main` | Production code | Requires PR + CI | app.bluemoxon.com |
| `staging` | Staging environment | Requires CI only | staging.app.bluemoxon.com |
| `feat/*` | Feature development | None | None |

### Workflow

1. Create feature branch from `staging`
2. Open PR targeting `staging`
3. CI runs, merge when passing
4. Deploy to staging automatically
5. Validate in staging environment
6. Open PR from `staging` to `main`
7. Merge to deploy to production

## AWS Authentication

We use AWS OIDC (OpenID Connect) for secure, keyless authentication. No long-lived AWS credentials are stored in GitHub.

### OIDC Configuration

GitHub Actions authenticates to AWS using:
- **OIDC Identity Provider** - Allows GitHub to authenticate with AWS
- **IAM Role** - `github-actions-deploy` with permissions for:
  - Lambda code updates
  - S3 bucket access (frontend, deploy, images)
  - CloudFront invalidation
  - Secrets Manager read access

### GitHub Secrets

| Secret | Purpose | Environment |
|--------|---------|-------------|
| `AWS_DEPLOY_ROLE_ARN` | Production deploy role ARN | production |
| `AWS_STAGING_DEPLOY_ROLE_ARN` | Staging deploy role ARN | staging |

### GitHub Environments

| Environment | Branch Restriction | Purpose |
|-------------|-------------------|---------|
| `production` | `main` only | Production deploys |
| `staging` | `staging` only | Staging deploys |

## Security Scanning

The CI pipeline includes comprehensive security scanning that **blocks deployment** on failures.

### Security Gates (All Blocking)

| Category | Tools | Blocks Deployment |
|----------|-------|-------------------|
| **SAST** | Bandit, Semgrep, Ruff (S rules) | Yes |
| **Dependency Scan** | pip-audit (Python), npm audit (Node.js) | Yes |
| **Secret Detection** | Trivy, Gitleaks | Yes |

### SAST (Static Application Security Testing)

**Bandit** - Python-specific security scanner
- Checks for common security issues (SQL injection, hardcoded passwords, etc.)
- Runs on all Python code in `app/`
- Fails on HIGH severity issues

**Semgrep** - Multi-language SAST
- Rules: `p/python`, `p/javascript`, `p/typescript`, `p/security-audit`, `p/owasp-top-ten`
- Covers Python, JavaScript/TypeScript, Vue templates
- Checks for OWASP Top 10 vulnerabilities

### Suppressing False Positives

```python
# Bandit
password = "test"  # nosec B105

# Ruff
local_path = "/tmp/test"  # noqa: S108

# Both
value = "/tmp/data"  # noqa: S108 # nosec B108
```

## Smoke Tests

After deployment, automated smoke tests verify:

1. **API Health** - `GET /api/v1/health/deep` returns 200
2. **Books API** - `GET /api/v1/books` returns valid pagination
3. **API Schema Validation** - Required fields exist on book responses (`id`, `title`, `status`, `inventory_type`)
4. **Data Integrity** - Validates data quality:
   - `source_url` format (must be full HTTP URL with item ID, not short alphanumeric - see #497)
   - `purchase_price` values (warns on `$0` prices - see #498)
5. **Frontend** - App loads with expected content
6. **Images** - Image URLs return proper `Content-Type: image/*`

If smoke tests fail:
- The workflow is marked as failed
- Changes are live (no automatic rollback)
- Check `gh run view <id> --log-failed` for details
- Manual rollback may be needed

## Version System

Version is **auto-generated at deploy time**:
- Format: `YYYY.MM.DD-<short-sha>` (e.g., `2025.12.06-9b22b0a`)
- Visible via `X-App-Version` response header
- Visible at `/api/v1/health/version` endpoint
- Git tag created on successful production deploy

## Dependency Updates

Dependabot creates PRs targeting `staging` branch:

| Ecosystem | Schedule | Target Branch |
|-----------|----------|---------------|
| Python (pip) | Weekly (Monday) | staging |
| npm | Weekly (Monday) | staging |
| GitHub Actions | Weekly (Monday) | staging |

Updates flow: Dependabot PR → staging → test → promote to main

## Local Development

The CI/CD pipeline doesn't affect local development:

```bash
# Backend
cd backend
poetry install
poetry run uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Files

```
.github/
├── workflows/
│   ├── ci.yml              # CI checks (PRs + pushes)
│   ├── deploy.yml          # Production deploy
│   ├── deploy-staging.yml  # Staging deploy (if exists separately)
│   ├── deploy-site.yml     # Marketing site deploy
│   └── terraform.yml       # Infrastructure plan
├── dependabot.yml          # Dependency updates (targets staging)
```

## Troubleshooting

### CI Failing

1. Check the workflow run in GitHub Actions
2. Review specific job logs for errors
3. Common issues:
   - Lint errors: Run `poetry run ruff check . --fix` locally
   - Type errors: Run `npm run type-check` locally
   - Test failures: Run `poetry run pytest -v` locally

### Deploy Failing

1. Check OIDC role permissions in AWS IAM
2. Verify deploy role ARN secret is correct
3. Check CloudWatch logs for Lambda errors
4. Verify S3 bucket permissions

### Smoke Tests Failing

1. Wait 30-60 seconds for CloudFront propagation
2. Check API health: `curl https://api.bluemoxon.com/api/v1/health/deep | jq`
3. Check Lambda logs in CloudWatch
4. Verify database connectivity

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [Validation Blueprint](VALIDATION.md) | Detailed linting, testing, formatting rules |
| [Deployment Guide](DEPLOYMENT.md) | Manual deploy procedures |
| [Infrastructure](INFRASTRUCTURE.md) | AWS resources |

---

*Last Updated: December 2025*
