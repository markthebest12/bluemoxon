# CI/CD Pipeline

BlueMoxon uses GitHub Actions for continuous integration and deployment. The pipeline ensures code quality, security, and reliable deployments.

## Overview

```
                    ┌─────────────────────────────────────────┐
                    │           GitHub Repository              │
                    └─────────────────────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │                                      │
            ┌───────▼───────┐                    ┌────────▼────────┐
            │   Pull Request │                    │  Push to Main    │
            └───────┬───────┘                    └────────┬────────┘
                    │                                      │
            ┌───────▼───────┐                    ┌────────▼────────┐
            │   CI Workflow  │                    │ Deploy Workflow  │
            │                │                    │                  │
            │  • Lint        │                    │  • CI Checks     │
            │  • Test        │                    │  • Build Lambda  │
            │  • Type Check  │                    │  • Build Frontend│
            │  • Security    │                    │  • Deploy to AWS │
            │  • Build       │                    │  • Smoke Tests   │
            └───────┬───────┘                    └────────┬────────┘
                    │                                      │
            ┌───────▼───────┐                    ┌────────▼────────┐
            │ PR Review Ready│                    │   Production    │
            └───────────────┘                    └─────────────────┘
```

## Workflows

### CI Workflow (`ci.yml`)

Runs on all pull requests and pushes to main. Ensures code quality before merge.

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

### Deploy Workflow (`deploy.yml`)

Runs on push to main (after CI passes). Deploys to production.

**Jobs:**

| Job | Description |
|-----|-------------|
| `ci` | Runs full CI workflow |
| `build-backend` | Creates Lambda deployment package with Docker |
| `build-frontend` | Builds Vue app for production |
| `deploy` | Uploads to S3, updates Lambda, invalidates CloudFront |
| `smoke-test` | Verifies API and frontend are working |

## AWS Authentication

We use AWS OIDC (OpenID Connect) for secure, keyless authentication. No long-lived AWS credentials are stored in GitHub.

### Setup OIDC

Run the setup script to create the required AWS resources:

```bash
./scripts/setup-github-oidc.sh
```

This creates:
1. **OIDC Identity Provider** - Allows GitHub to authenticate with AWS
2. **IAM Role** - `github-actions-deploy` with permissions for:
   - Lambda code updates
   - S3 frontend bucket access
   - CloudFront invalidation

### Configure GitHub Secret

After running the setup script, add the role ARN to GitHub:

```bash
# Using GitHub CLI
gh secret set AWS_DEPLOY_ROLE_ARN --body 'arn:aws:iam::266672885920:role/github-actions-deploy'

# Or via GitHub UI
# Settings → Secrets and variables → Actions → New repository secret
```

### GitHub Environment

Create a `production` environment in GitHub for deployment protection:

1. Go to Settings → Environments → New environment
2. Name: `production`
3. Configure protection rules:
   - Required reviewers (optional)
   - Wait timer (optional)
   - Restrict to specific branches: `main`

## Local Development

The CI/CD pipeline doesn't affect local development. Continue using:

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

## Manual Deployment

If needed, you can deploy manually:

```bash
# Backend Lambda
docker run --rm \
  -v $(pwd)/backend:/app:ro \
  -v /tmp/lambda-deploy:/output \
  --platform linux/amd64 \
  amazonlinux:2023 \
  /bin/bash -c "
    dnf install -y python3.11 python3.11-pip zip > /dev/null 2>&1
    python3.11 -m pip install -q -t /output -r /app/requirements.txt
    cp -r /app/app /output/
  "

cd /tmp/lambda-deploy
zip -r /tmp/bluemoxon-api.zip . -x "*.pyc" -x "*__pycache__*"

aws s3 cp /tmp/bluemoxon-api.zip s3://bluemoxon-frontend/lambda/bluemoxon-api.zip --profile bluemoxon
aws lambda update-function-code \
  --function-name bluemoxon-api \
  --s3-bucket bluemoxon-frontend \
  --s3-key lambda/bluemoxon-api.zip \
  --profile bluemoxon --region us-west-2

# Frontend
cd frontend
npm run build
aws s3 sync dist/ s3://bluemoxon-frontend/ --profile bluemoxon --region us-west-2
aws cloudfront create-invalidation \
  --distribution-id E16BJX90QWQNQO \
  --paths "/*" \
  --profile bluemoxon
```

## Dependency Updates

Dependabot is configured to automatically create PRs for dependency updates:

- **Python** (backend): Weekly on Mondays
- **npm** (frontend): Weekly on Mondays
- **GitHub Actions**: Weekly on Mondays

Updates are grouped by type to reduce PR noise.

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

**Ruff Security Rules (S)** - Integrated in linting
- Equivalent to flake8-bandit rules
- Runs as part of backend-lint job

### Dependency Scanning

**pip-audit** (Python)
- Scans `requirements.txt` for known vulnerabilities
- Uses OSV vulnerability database
- Blocks on ANY known vulnerability (`--strict`)

**npm audit** (Node.js)
- Scans `package-lock.json` for vulnerabilities
- Blocks on HIGH or CRITICAL severity

### Secret Detection

**Trivy**
- Scans filesystem for hardcoded secrets
- Checks for API keys, tokens, passwords
- Blocks on HIGH/CRITICAL findings

**Gitleaks**
- Scans git history for leaked secrets
- Runs on full commit history
- Warning only (license required for exit codes)

### Suppressing False Positives

For intentional security exceptions (e.g., test data, local dev paths):

```python
# Bandit
password = "test"  # nosec B105

# Ruff
local_path = "/tmp/test"  # noqa: S108

# Both
value = "/tmp/data"  # noqa: S108 # nosec B108
```

### Security Reports

Security scan artifacts are uploaded and retained for 30 days:
- `bandit-report.json` - Detailed Bandit findings

## Smoke Tests

After deployment, automated smoke tests verify:

1. **API Health** - `GET /health` returns 200
2. **Books API** - `GET /api/v1/books` returns valid pagination
3. **Frontend** - `GET https://bluemoxon.com` returns HTML
4. **Images** - Presigned URL redirects work

If smoke tests fail, the deployment is marked as failed but changes are live. Manual rollback may be needed.

## Rollback

To rollback a bad deployment:

```bash
# Find previous Lambda version
aws lambda list-versions-by-function \
  --function-name bluemoxon-api \
  --profile bluemoxon --region us-west-2

# Rollback Lambda (if versions are enabled)
# Or redeploy from previous commit

# Frontend rollback
git checkout <previous-commit>
cd frontend && npm run build
aws s3 sync dist/ s3://bluemoxon-frontend/ --profile bluemoxon
aws cloudfront create-invalidation --distribution-id E16BJX90QWQNQO --paths "/*" --profile bluemoxon
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
2. Verify `AWS_DEPLOY_ROLE_ARN` secret is set correctly
3. Check CloudWatch logs for Lambda errors
4. Verify S3 bucket permissions

### Smoke Tests Failing

1. Wait 30-60 seconds for CloudFront propagation
2. Check API health: `curl https://api.bluemoxon.com/health`
3. Check Lambda logs in CloudWatch
4. Verify database connectivity

## Files

```
.github/
├── workflows/
│   ├── ci.yml              # CI pipeline
│   └── deploy.yml          # Deploy pipeline
└── dependabot.yml          # Dependency updates

scripts/
└── setup-github-oidc.sh    # AWS OIDC setup
```
