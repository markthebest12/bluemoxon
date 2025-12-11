# BlueMoxon (bmx) Project Instructions

## Bash Command Formatting

**CRITICAL: NEVER use complex shell syntax in bash commands.** These cause permission prompts that cannot be auto-approved:

**NEVER use:**
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` or `$((...))` command/arithmetic substitution
- `||` or `&&` chaining (even simple chaining breaks auto-approve)

**ENFORCEMENT**: If you catch yourself about to use `&&`, STOP. Make separate sequential Bash tool calls instead. The permission dialog toil from `&&` is enormous - one prompt per chained command.

```bash
# BAD - will ALWAYS prompt:
# Check API health
curl -s https://api.example.com/health

aws lambda get-function-configuration \
  --function-name my-function

AWS_PROFILE=staging aws logs filter-log-events --start-time $(date +%s000) | jq '.events'

# GOOD - simple single-line commands only:
curl -s https://api.example.com/health
aws lambda get-function-configuration --function-name my-function --query 'Environment'
AWS_PROFILE=staging aws sts get-caller-identity
AWS_PROFILE=staging aws logs filter-log-events --log-group-name /aws/lambda/my-func --limit 10
```

Use the command description field instead of inline comments.

## BMX API Calls

Use `bmx-api` for all BlueMoxon API calls (no permission prompts):

```bash
bmx-api GET /books                          # List books (staging)
bmx-api GET /books/123                      # Get specific book
bmx-api POST /books '{"title":"..."}'       # Create book
bmx-api PUT /books/123 '{"title":"..."}'    # Full update
bmx-api PATCH /books/123 '{"status":"..."}'  # Partial update
bmx-api DELETE /books/123                   # Delete book
bmx-api --prod GET /books                   # Production (explicit)
bmx-api --text-file analysis.md PUT /books/123/analysis  # Upload text/plain content
bmx-api --prod --text-file analysis.md PUT /books/123/analysis  # Production text upload
bmx-api --image photo.jpg POST /books/123/images  # Upload image (multipart)
bmx-api --prod --image photo.jpg POST /books/123/images  # Production image upload
```

Default is staging. Use `--prod` flag for production.

**Flags:**
- `--prod` - Use production API instead of staging
- `--text-file FILE` - Send file contents with `Content-Type: text/plain` (for analysis uploads)
- `--image FILE` - Upload image with `multipart/form-data` (for image uploads)

Keys stored in `~/.bmx/staging.key` and `~/.bmx/prod.key` (600 permissions).

## Permission Pattern Guidelines

When adding patterns to `~/.claude/settings.json`:

1. **Use absolute paths, not `~`** - Pattern matching doesn't expand tilde
   - BAD: `Bash(cat ~/.aws/config:*)`
   - GOOD: `Bash(cat /Users/mark/.aws/config:*)`

2. **`VAR=:*` patterns don't work** - Must include part of the value
   - BAD: `Bash(AWS_PROFILE=:*)`
   - GOOD: `Bash(AWS_PROFILE=staging:*)`, `Bash(AWS_PROFILE=prod:*)`

3. **Patterns with `#` don't work reliably** - Avoid comment prefixes in commands

4. **Sessions must restart to pick up permission changes** - Use `Ctrl-D` then `claude -r`

5. **Permission hierarchy** (later overrides earlier):
   - `~/.claude/settings.json` (global)
   - `<project>/.claude/settings.json` (project/team)
   - `<project>/.claude/settings.local.json` (project/personal)

6. **MCP tool wildcards may not work**: `mcp__playwright__*` should work but often doesn't. List each tool explicitly instead (e.g., `mcp__playwright__browser_navigate`, `mcp__playwright__browser_click`, etc.)

7. **Deny rules take precedence** over allow rules

8. **"Don't ask again" writes to local project file**, not global - clean up local files periodically and consolidate to global

9. **Pattern format**: `Bash(command:*)` - the `:*` suffix means "starts with this prefix"

10. **For new commands**, add to global `~/.claude/settings.json` not project-local files

---

## CRITICAL: CI/CD Workflow Requirements

**NEVER push directly to main.** All changes MUST go through the CI/CD pipeline:

### Required Workflow for ALL Code Changes

```bash
# 1. Create feature branch (use conventional naming)
git checkout -b <type>/<description>
# Types: feat/, fix/, refactor/, docs/, chore/, perf/

# 2. Make changes

# 3. Run local validation BEFORE committing (REQUIRED)
# Run these as separate commands (NOT chained with &&):
poetry run ruff check backend/
poetry run ruff format --check backend/
npm run --prefix frontend lint
npm run --prefix frontend type-check

# 4. Commit with conventional commit message
git commit -m "<type>: <description>"

# 5. Push branch and create PR
git push -u origin <branch-name>
gh pr create --title "<type>: <description>" --body "## Summary\n- <changes>\n\n## Test Plan\n- [ ] CI passes"

# 6. Wait for CI to pass on PR (DO NOT PROCEED IF CI FAILS)
gh pr checks <pr-number> --watch

# 7. Merge ONLY after CI passes (use auto-merge when available)
gh pr merge <pr-number> --squash --delete-branch --auto
```

### Auto-Deploy Flow
- Push to main triggers Deploy workflow
- Deploy workflow runs CI checks first
- If CI passes, deploys to production automatically
- Creates version tag: v{YYYY.MM.DD}-{short-sha}

### CRITICAL: Post-Deploy Validation

**ALWAYS watch the deploy workflow after merging to main.** CI passing does NOT guarantee the deploy succeeds - smoke tests run AFTER deployment.

```bash
# Watch deploy workflow after merge
gh run list --workflow Deploy --limit 1   # Get run ID
gh run watch <run-id> --exit-status       # Watch until complete

# Or check deploy status
gh run list --workflow Deploy
```

**Smoke tests verify:**
- API health endpoint returns 200
- Books API returns paginated response
- Frontend loads with expected content
- **Image URLs return `Content-Type: image/*`** (not error pages)

**If smoke tests fail:**
1. Check the failed step: `gh run view <run-id> --log-failed`
2. Fix the issue on a new branch
3. The failed deploy did NOT create a release tag

### Version Tagging
Tags are automatically created on successful deploy. Manual tagging:
```bash
# For releases
git tag -a v1.0.0 -m "Release description"
git push origin v1.0.0
```

## CRITICAL: Staging-First Workflow

**ALL changes MUST go through staging before production.** This is mandatory for:
- Feature branches
- Bug fixes
- Dependency updates (Dependabot targets `staging` branch)
- Infrastructure changes

### Exception: Marketing Website Only
The marketing site (`site/index.html`) has no staging environment and deploys directly to production. This is the ONLY exception to staging-first.

### Required Flow for ALL Changes

```
Feature Branch → Staging → Production
       ↓             ↓          ↓
    PR to staging  Deploy   PR staging→main
                   + Test      Deploy
```

1. **Create PR targeting `staging`** (NOT `main`)
2. **Merge to staging** after CI passes
3. **Validate in staging environment** (manual or automated)
4. **Create PR from `staging` to `main`** to promote to production
5. **Merge to main** after approval

### Dependabot Configuration
Dependabot is configured to target `staging` branch for all ecosystems:
- Python backend (`pip`)
- Frontend (`npm`)
- GitHub Actions (`github-actions`)

This ensures dependency updates are tested in staging before reaching production.

### Why Staging-First Matters
- Catches issues before they reach production
- Provides validation environment with real AWS services
- Allows testing with production-like data (via DB sync)
- Prevents "works on my machine" deployments

### Anti-Patterns (DO NOT DO)
- ❌ PR directly to `main` (except marketing site)
- ❌ Merging untested code to production
- ❌ Skipping staging "because it's a small change"
- ❌ Manual dependency updates bypassing staging

## Branching Strategy (GitFlow)

```
main ─────●─────●─────●─────→  [Production: app.bluemoxon.com]
           \     \     \
staging ────●─────●─────●────→  [Staging: staging.app.bluemoxon.com]
             \   / \   /
feature ──────●     ●────────→  [Feature branches]
```

### Branch Purposes
| Branch | Purpose | Protection | Deploy Target |
|--------|---------|------------|---------------|
| `main` | Production code | Requires PR + CI + 1 approval | app.bluemoxon.com |
| `staging` | Staging environment | Requires CI only | staging.app.bluemoxon.com |
| `feat/*` | Feature development | None | None |

### Workflow Examples
```bash
# Standard feature → staging → production (CORRECT)
git checkout staging
git pull origin staging
git checkout -b feat/my-feature
# ... make changes ...
gh pr create --base staging --title "feat: My feature"
# After merge to staging and validation:
gh pr create --base main --head staging --title "chore: Promote staging to production"

# Marketing site ONLY (exception - no staging)
git checkout -b fix/landing-page
# ... changes to site/index.html only ...
gh pr create --base main --title "fix: Update landing page"

# WRONG - DO NOT DO THIS (except marketing site)
gh pr create --base main  # ❌ Skips staging!
```

## Staging Environment

### URLs
| Service | URL |
|---------|-----|
| Frontend | https://staging.app.bluemoxon.com |
| API | https://staging.api.bluemoxon.com |
| Health Check | https://staging.api.bluemoxon.com/api/v1/health/deep |

### AWS Profile
Use `AWS_PROFILE=staging` for all staging AWS commands:
```bash
AWS_PROFILE=staging aws lambda list-functions
AWS_PROFILE=staging aws logs tail /aws/lambda/bluemoxon-staging-api --since 5m
```

### Database Sync (Prod → Staging)
Sync production data to staging via Lambda:
```bash
aws lambda invoke --function-name bluemoxon-staging-db-sync --profile staging --payload '{}' .tmp/sync-response.json
cat .tmp/sync-response.json | jq
```

Watch sync progress:
```bash
AWS_PROFILE=staging aws logs tail /aws/lambda/bluemoxon-staging-db-sync --follow
```

See [docs/DATABASE_SYNC.md](docs/DATABASE_SYNC.md) for full details.

### Staging Authentication (Separate Cognito Pool)

Staging uses its own Cognito user pool, separate from production. This provides full isolation but requires manual user management.

**Staging Cognito Config:**
```
Pool ID: us-west-2_5pOhFH6LN
Client ID: 7h1b144ggk7j4dl9vr94ipe6k5
Domain: bluemoxon-staging.auth.us-west-2.amazoncognito.com
```

**Create/Reset a staging user:**
```bash
# Create user (or skip if exists)
AWS_PROFILE=staging aws cognito-idp admin-create-user --user-pool-id us-west-2_5pOhFH6LN --username user@example.com --user-attributes Name=email,Value=user@example.com Name=email_verified,Value=true

# Set permanent password
AWS_PROFILE=staging aws cognito-idp admin-set-user-password --user-pool-id us-west-2_5pOhFH6LN --username user@example.com --password 'YourPassword123!' --permanent

# Map Cognito sub to database (run after creating user)
AWS_PROFILE=staging aws lambda invoke --function-name bluemoxon-staging-db-sync --payload '{"cognito_only": true}' --cli-binary-format raw-in-base64-out .tmp/sync.json
```

**Troubleshooting login issues:**
1. **"Invalid email or password"** - Clear browser localStorage, retry with fresh session
2. **User not in API response** - Run `cognito_only` sync to map Cognito sub to DB
3. **Case sensitivity** - Staging Cognito is case-sensitive; use exact email case

### Related Documentation
- [docs/STAGING_ENVIRONMENT_PLAN.md](docs/STAGING_ENVIRONMENT_PLAN.md) - Architecture and setup
- [docs/DATABASE_SYNC.md](docs/DATABASE_SYNC.md) - Data sync procedures
- [docs/STAGING_INFRASTRUCTURE_CHANGES.md](docs/STAGING_INFRASTRUCTURE_CHANGES.md) - Manual changes to terraformize

## Version System

Version is **auto-generated at deploy time** - no manual maintenance required.

**Format:** `YYYY.MM.DD-<short-sha>` (e.g., `2025.12.06-9b22b0a`)

### Version Visibility
| Location | How to Check |
|----------|--------------|
| API Response Header | `X-App-Version` header on ALL responses |
| API Endpoint | `GET /api/v1/health/version` |
| Frontend Config | `import { APP_VERSION } from '@/config'` |
| Deploy Info | `GET /api/v1/health/info` (includes git SHA, deploy time) |

### How It Works
- `VERSION` file in repo is `0.0.0-dev` (placeholder for local dev)
- Deploy workflow generates version: `YYYY.MM.DD-<short-sha>`
- Version is injected into Lambda package and frontend build
- Smoke tests validate deployed version matches expected

### Running Database Migrations

Since Aurora is in a private VPC with no bastion host, run migrations via the `/health/migrate` endpoint:

```bash
# Run migrations in staging
curl -X POST https://staging.api.bluemoxon.com/api/v1/health/migrate

# Run migrations in production (CAUTION: verify in staging first!)
curl -X POST https://api.bluemoxon.com/api/v1/health/migrate
```

This endpoint:
- Runs all pending Alembic migrations
- Returns success/failure status with details
- Is idempotent (safe to run multiple times)

**When to use:**
- After deploying code that includes new migrations
- If you see "duplicate key" or sequence-related errors
- After manual database operations

## Token-Saving Guidelines

### CRITICAL: Use Scripts Instead of Claude for These Tasks

```bash
# Full workflow - validates, commits, creates PR, waits for CI, merges
./scripts/validate-and-push.sh "fix: description here"

# Setup pre-commit hooks (run once)
./scripts/setup-dev.sh
```

### DO NOT use Claude tokens for:
| Task | Use Instead |
|------|-------------|
| Running linters | `pre-commit run --all-files` |
| Waiting for CI | `gh pr checks <n> --watch` |
| Checking PR status | `gh pr checks <n>` |
| Formatting code | `poetry run ruff format .` or `npm run lint` |
| Validating before push | `./scripts/validate-and-push.sh` |
| Checking deploy status | `gh run list --workflow Deploy` |

### Pre-commit Hooks (run automatically on commit)
- `ruff check --fix` (Python linting with auto-fix)
- `ruff format` (Python formatting)
- `npm run lint` (Frontend linting)
- `npm run type-check` (TypeScript checking)

### Use Claude for:
- Writing new code/features
- Debugging complex issues
- Architecture decisions
- Code review insights
- AWS infrastructure changes

### One-Command Workflow
After making changes, run:
```bash
./scripts/validate-and-push.sh "type: description"
```
This script:
1. Runs all linters/formatters locally
2. Commits and pushes to branch
3. Creates PR
4. Waits for CI to pass
5. Merges to main automatically

**Claude should NOT manually run these steps - the script handles them.**

## Temporary Files

**MUST use `.tmp/` for all temporary files** - NEVER use `/tmp`:
```bash
.tmp/                  # Project-local temp directory (gitignored)
```

**ENFORCEMENT**: Using `/tmp` triggers permission prompts. `.tmp/` is pre-approved. Always use `.tmp/`.

Benefits:
- No permission prompts (covered by project permissions)
- Stays with project context
- Auto-cleaned on project deletion

Examples:
```bash
# Download files
curl -o .tmp/response.json https://api.example.com/data

# Script outputs
python script.py > .tmp/output.txt

# Temporary processing
aws lambda invoke --payload '{}' .tmp/result.json
```

## Local Development Strategy

**Minimal local dev - no Docker required for daily work.**

### What to run locally:
| Component | Command | Purpose |
|-----------|---------|---------|
| Frontend | `npm run dev` | Hot reload for UI changes |
| Backend tests | `poetry run pytest` | Fast unit tests (uses SQLite) |
| Linting | Pre-commit hooks | Auto-runs on commit |

### What runs in AWS only:
- PostgreSQL (Aurora) - tests use SQLite in-memory
- Cognito auth - tests mock auth, API key bypasses it
- S3 images - not needed for most development
- CloudWatch - production monitoring only

### Service Bypasses (already configured):
- **Database**: `conftest.py` uses SQLite when `DATABASE_URL` not set
- **Cognito**: Returns "skipped" when `cognito_user_pool_id` empty
- **Auth in tests**: Mocked with `get_mock_editor()`
- **API Key**: `X-API-Key` header bypasses Cognito entirely

### When you DO need full local stack:
```bash
# Only if debugging database-specific issues
docker-compose up -d postgres
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

## Project Structure

```
bluemoxon/
├── VERSION           # App version (single source of truth)
├── .tmp/             # Temporary files (gitignored)
├── backend/           # FastAPI + SQLAlchemy
│   ├── app/          # Application code
│   └── tests/        # pytest tests
├── frontend/         # Vue 3 + TypeScript
│   └── src/          # Source code
├── infra/            # AWS infrastructure docs
├── docs/             # Project documentation
│   └── STAGING_ENVIRONMENT_PLAN.md  # Staging setup guide
└── .github/workflows/
    ├── ci.yml        # Runs on PRs to main
    └── deploy.yml    # Runs on push to main
```

## AWS Resources

- **API**: Lambda `bluemoxon-api` + API Gateway
- **Frontend**: S3 `bluemoxon-frontend` + CloudFront
- **Images**: S3 `bluemoxon-images` + CloudFront CDN
- **Database**: RDS PostgreSQL
- **Auth**: Cognito User Pool (separate pools per environment)

## CRITICAL: Lambda Python Version Requirements

**Lambda runtime and build image MUST use the same Python version.**

### Why This Matters
Packages like `pydantic` contain compiled binary extensions (`pydantic_core._pydantic_core`) that are:
- Python-version-specific (e.g., compiled for Python 3.12 won't work on 3.11)
- Platform-specific (must be built on Linux x86_64 for Lambda)

### Current Configuration
| Component | Python Version | Source |
|-----------|---------------|--------|
| Lambda Runtime | Python 3.12 | Terraform `lambda` module |
| Deploy Build Image | `public.ecr.aws/lambda/python:3.12` | `deploy.yml`, `deploy-staging.yml` |
| CI Tests | Python 3.11 | `ci.yml` (doesn't need to match) |

### When Changing Python Versions
1. Update Lambda runtime in Terraform: `infra/terraform/modules/lambda/main.tf`
2. Update deploy build image in **BOTH** workflows:
   - `.github/workflows/deploy.yml`
   - `.github/workflows/deploy-staging.yml`
3. Deploy staging first to validate
4. Update CI Python version if needed (optional, for consistency)

### Symptoms of Version Mismatch
```
[ERROR] Runtime.ImportModuleError: Unable to import module 'app.main': No module named 'pydantic_core._pydantic_core'
```

## CRITICAL: Infrastructure as Code (Terraform)

**ALL infrastructure MUST be managed via Terraform.** No manual AWS console changes.

### Why This Matters
- Manual changes create drift that's impossible to track
- Manual changes get lost when resources are recreated
- Other team members don't know about manual changes
- Rollbacks become impossible
- Staging/prod parity breaks

### The Rule
1. **NEVER** create/modify AWS resources manually (console or CLI)
2. **ALWAYS** add infrastructure changes to `infra/terraform/`
3. **DOCUMENT** any temporary manual fixes immediately in docs and create a ticket to terraformize

### Workflow for Infrastructure Changes
```bash
cd infra/terraform

# 1. Make changes to .tf files
# 2. Plan (always review!)
terraform plan -var-file=envs/staging.tfvars

# 3. Apply
terraform apply -var-file=envs/staging.tfvars

# 4. Commit the .tf changes (run as separate commands)
git add .
git commit -m "infra: Add/change X resource"
```

### Import Existing Resources
If a resource was created manually, import it before making changes:
```bash
terraform import 'module.cognito.aws_cognito_user_pool.this' us-west-2_POOLID
```

### Current State
- **Staging:** Terraform state in `s3://bluemoxon-terraform-state-staging`
- **Prod:** Migration in progress (see `docs/PROD_MIGRATION_CHECKLIST.md`)

### Exception Process (Emergency Fixes ONLY)

If you MUST make a manual change (emergency fix):

1. **Document BEFORE making the change:**
   - Create entry in `docs/STAGING_INFRASTRUCTURE_CHANGES.md` or `docs/PROD_INFRASTRUCTURE_CHANGES.md`
   - Include: resource type, ID, what changed, why

2. **Make the change** with AWS CLI (auditable) not console:
   ```bash
   # Good: auditable command
   aws lambda update-function-configuration --function-name X --environment ...

   # Bad: console clicks (no record)
   ```

3. **Immediately create follow-up issue:**
   - Create GitHub issue: "infra: Terraformize [resource]"
   - Link to the documentation entry

4. **Notify team** in PR or Slack

**Manual change without documentation = grounds for revert.**

### Terraform Quick Reference

| Task | Command |
|------|---------|
| Format | `terraform fmt -recursive` |
| Validate | `terraform validate` |
| Plan (staging) | `AWS_PROFILE=staging terraform plan -var-file=envs/staging.tfvars -var="db_password=X"` |
| Apply (staging) | `AWS_PROFILE=staging terraform apply -var-file=envs/staging.tfvars -var="db_password=X"` |
| Check drift | `AWS_PROFILE=staging terraform plan -detailed-exitcode -var-file=envs/staging.tfvars` |
| Import resource | `terraform import 'module.name.resource.name' <aws-id>` |
| Show state | `terraform state list` |
| Remove from state | `terraform state rm <resource>` |

**Exit codes for drift detection:**
- `0` = No changes (infrastructure matches config)
- `1` = Error
- `2` = Changes detected (drift!)

### Terraform Validation Testing (Destroy/Apply)

**For significant infrastructure changes, validate with destroy/apply cycle in staging:**

```bash
cd infra/terraform

# 1. Create RDS snapshot (data protection)
AWS_PROFILE=staging aws rds create-db-snapshot \
  --db-instance-identifier bluemoxon-staging-db \
  --db-snapshot-identifier pre-terraform-test-$(date +%Y%m%d)

# 2. Destroy staging infrastructure
AWS_PROFILE=staging terraform destroy \
  -var-file=envs/staging.tfvars \
  -var="db_password=$STAGING_DB_PASSWORD"

# 3. Apply from scratch
AWS_PROFILE=staging terraform apply \
  -var-file=envs/staging.tfvars \
  -var="db_password=$STAGING_DB_PASSWORD"

# 4. Validate services
curl -s https://staging.api.bluemoxon.com/api/v1/health/deep | jq
curl -s https://staging.app.bluemoxon.com | head -20
```

**When to use destroy/apply testing:**
- Adding new Terraform modules
- Changing VPC networking (endpoints, NAT gateway)
- Major IAM policy changes
- Before migrating configuration to production
- After significant module refactoring

**What survives destroy/apply (external to Terraform):**
- ACM certificates (passed as ARNs)
- Route53 records (in prod account)
- RDS snapshots (manual backup)
- S3 bucket data (if buckets not destroyed)

## CRITICAL: Terraform Style Requirements

**STRICTLY follow HashiCorp's official guidelines:**
- Style Guide: https://developer.hashicorp.com/terraform/language/style
- Module Pattern: https://developer.hashicorp.com/terraform/tutorials/modules/pattern-module-creation

### File Organization (REQUIRED)
```
modules/<module-name>/
├── main.tf          # Resources and data sources
├── variables.tf     # Input variables (ALPHABETICAL order)
├── outputs.tf       # Output values (ALPHABETICAL order)
├── versions.tf      # Provider version constraints (if needed)
└── README.md        # Module documentation
```

### Variable Definitions (REQUIRED for ALL variables)
```hcl
variable "example_name" {
  type        = string
  description = "Human-readable description of what this variable controls"
  default     = "sensible-default"  # Optional variables MUST have defaults

  validation {  # Add validation where appropriate
    condition     = length(var.example_name) > 0
    error_message = "Example name cannot be empty."
  }
}
```

### Naming Conventions
- **Resources**: Use descriptive nouns, underscore-separated: `aws_lambda_function`, NOT `aws-lambda-function`
- **Variables**: Underscore-separated, descriptive: `db_instance_class`, NOT `dbInstanceClass`
- **Do NOT include resource type in name**: `name = "api"`, NOT `name = "lambda-api"`

### Resource Organization Order
1. `count` or `for_each` meta-arguments
2. Resource-specific non-block parameters
3. Resource-specific block parameters
4. `lifecycle` blocks (if needed)
5. `depends_on` (if required)

### Module Design Principles
1. **Single Purpose**: Each module does ONE thing well
2. **80% Use Case**: Design for common cases, avoid edge case complexity
3. **Expose Common Args**: Only expose frequently-modified arguments
4. **Output Everything**: Export all useful values even if not immediately needed
5. **Sensible Defaults**: Required inputs have no default; optional inputs have good defaults

### Before Committing ANY Terraform Changes
```bash
cd infra/terraform
terraform fmt -recursive      # Format all files
terraform validate            # Validate syntax
terraform plan -var-file=envs/staging.tfvars  # Review changes
```

### Environment Separation (CRITICAL for Prod/Staging)
- Use `envs/staging.tfvars` and `envs/prod.tfvars` for environment-specific values
- NEVER hardcode environment-specific values in modules
- Use variables with environment passed from tfvars
- State files are separate: `bluemoxon/staging/terraform.tfstate` vs `bluemoxon/prod/terraform.tfstate`

## Troubleshooting: Deep Health Check Failures

**ALWAYS check `/api/v1/health/deep` first when debugging API issues.** This endpoint validates all dependencies.

### Common Failure: "Service Unavailable" (503) with Lambda Timeout

**Symptom:** Deep health times out at 30 seconds, returns `{"message": "Service Unavailable"}`

**Root Cause:** Lambda in VPC cannot reach AWS services (S3, Cognito, Secrets Manager)

**Diagnosis:**
```bash
curl -s "https://staging.api.bluemoxon.com/api/v1/health/deep"
curl -s "https://staging.api.bluemoxon.com/api/v1/books?limit=1"
```
If books works but deep health times out → VPC endpoint issue

**Fix:** Ensure VPC has required endpoints:
- `com.amazonaws.us-west-2.secretsmanager` (Interface) - for DB credentials
- `com.amazonaws.us-west-2.s3` (Gateway) - for images bucket
- `com.amazonaws.us-west-2.cognito-idp` (Interface) - for Cognito API

See `docs/PROD_MIGRATION_CHECKLIST.md` → "VPC Networking Requirements" section.

### Common Failure: S3 Bucket Deleted

**Symptom:** Deep health check hangs on S3 check

**Diagnosis:**
```bash
AWS_PROFILE=staging aws s3 ls s3://bluemoxon-staging-images
```
If "NoSuchBucket" → bucket was deleted

**Fix:**
```bash
AWS_PROFILE=staging aws s3 mb s3://bluemoxon-staging-images --region us-west-2
```

### Debugging Steps

1. Check simple health: `curl https://staging.api.bluemoxon.com/health`
2. Check Lambda logs: `AWS_PROFILE=staging aws logs tail /aws/lambda/bluemoxon-staging-api --since 5m`
3. Look for "timeout" in logs → VPC networking issue
4. Check VPC endpoints exist for S3/Cognito/Secrets Manager
5. Check S3 bucket exists

## Quick Commands

```bash
# Backend
cd backend
poetry install              # Install deps
poetry run ruff check .     # Lint
poetry run ruff format .    # Format
poetry run pytest           # Test

# Frontend
cd frontend
npm install                 # Install deps
npm run lint               # Lint + fix
npm run type-check         # TypeScript check
npm run build              # Production build
npm run dev                # Dev server

# Git/CI
gh pr create               # Create PR
gh pr checks <n> --watch   # Watch CI on PR
gh pr merge <n> --squash --auto  # Auto-merge when CI passes
gh run list --workflow Deploy    # Check deploy status
gh run watch <id> --exit-status  # Watch deploy + smoke tests (REQUIRED after merge)
```
