# BlueMoxon (bmx) Project Instructions

## Bash Command Formatting

**CRITICAL: NEVER use complex shell syntax in bash commands.** These cause permission prompts that cannot be auto-approved:

**NEVER use:**
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` or `$((...))` command/arithmetic substitution
- `||` or `&&` chaining (even simple chaining breaks auto-approve)
- `!` in quoted strings (bash history expansion corrupts values like passwords)
  - BAD: `--password 'Test1234!'` → `!` gets expanded/corrupted
  - GOOD: `--password 'Test@1234'` → use `@`, `#`, `$` instead of `!`

**ENFORCEMENT**: If you catch yourself about to use `&&`, STOP. Make separate sequential Bash tool calls instead. The permission dialog toil from `&&` is enormous - one prompt per chained command.

```bash
# BAD - will ALWAYS prompt:
# Check API health
curl -s https://api.example.com/health

aws lambda get-function-configuration \
  --function-name my-function

AWS_PROFILE=bmx-staging aws logs filter-log-events --start-time $(date +%s000) | jq '.events'

# GOOD - simple single-line commands only:
curl -s https://api.example.com/health
aws lambda get-function-configuration --function-name my-function --query 'Environment'
AWS_PROFILE=bmx-staging aws sts get-caller-identity
AWS_PROFILE=bmx-staging aws logs filter-log-events --log-group-name /aws/lambda/my-func --limit 10
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
   - GOOD: `Bash(AWS_PROFILE=bmx-staging:*)`, `Bash(AWS_PROFILE=bmx-prod:*)`

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

### Deploy Configuration

**Deploy configuration is auto-synced from Terraform outputs** - no manual updates needed. The deploy workflow reads values directly from Terraform state (see [docs/CI_CD.md](docs/CI_CD.md) for details).

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

### CRITICAL: Deferred Work Must Have GitHub Issues

**When work is deferred, ALWAYS create a GitHub issue immediately.** Don't leave deferred items buried in PR comments or issue threads.

**Required for deferred work:**
```bash
gh issue create --title "feat/fix: [Description] (Phase X of #NNN)" --body "$(cat <<'EOF'
## Background
Deferred from #NNN ([original issue title]). See original issue for full context.

## Problem
[What's not working or missing]

## Root Cause (if known)
[Technical details from investigation]

## Solution
[Proposed fix]

## Files to Modify
- `path/to/file.py` - [what needs to change]

## Related
- Parent: #NNN
- Depends on: #XXX (if any)
EOF
)"
```

**Why this matters:**
- Deferred work in comments gets lost
- Future sessions need issue numbers to find context
- Enables proper prioritization and sprint planning
- Creates audit trail of technical debt

**Anti-patterns (DO NOT DO):**
- ❌ "Phases 3-5 can be done later" (in PR comment)
- ❌ "Future work: add X" (in code comment)
- ❌ "TODO: fix this properly" (without issue link)

**Correct pattern:**
- ✅ Close current issue with "Phases 1-2 complete, see #276, #277, #278 for remaining work"
- ✅ Each deferred phase gets its own trackable issue
- ✅ Issues reference parent for context breadcrumbs

### CRITICAL: Merge Conflict Resolution

**After resolving ANY merge conflict, ALWAYS verify no duplicate code was introduced.**

Merge conflicts in Python files can easily result in duplicate function definitions when the same code appears both inside and outside conflict markers.

**Required verification after conflict resolution:**
```bash
# Check for duplicate function definitions
grep -n "def function_name" path/to/file.py

# Run lint to catch redefinitions (F811 error)
poetry run ruff check backend/
```

**Common failure mode:**
When merging staging→main, if both branches modified the same file, the conflict markers may include code that ALSO exists after the markers. Keeping "both sides" creates duplicates.

**Prevention checklist:**
1. After resolving conflicts, search for `def ` to verify each function is defined only once
2. Run `ruff check` before committing the merge
3. If CI fails with F811 (redefinition), the merge introduced duplicate code

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

| Service | URL |
|---------|-----|
| Frontend | https://staging.app.bluemoxon.com |
| API | https://staging.api.bluemoxon.com |
| Health Check | https://staging.api.bluemoxon.com/api/v1/health/deep |

**AWS Profile:** Use `AWS_PROFILE=bmx-staging` for all staging AWS commands.

See [docs/OPERATIONS.md](docs/OPERATIONS.md) for:
- Database sync (prod → staging)
- User management (create/reset staging users)
- Authentication troubleshooting

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

See [docs/OPERATIONS.md](docs/OPERATIONS.md) for migration procedures via `/health/migrate` endpoint.

## Token-Saving Guidelines

**Use scripts, not Claude, for repetitive tasks:**

```bash
./scripts/validate-and-push.sh "fix: description"  # Full workflow: lint, commit, PR, CI, merge
./scripts/setup-dev.sh                              # Setup pre-commit hooks (once)
```

| Don't Use Claude For | Use Instead |
|---------------------|-------------|
| Running linters | `pre-commit run --all-files` |
| Waiting for CI | `gh pr checks <n> --watch` |
| Formatting code | `poetry run ruff format .` |
| Checking deploy | `gh run list --workflow Deploy` |

**Use Claude for:** Writing code, debugging, architecture decisions, code review insights.

## Temporary Files

**MUST use `.tmp/` for all temporary files** - NEVER use `/tmp`.

Using `/tmp` triggers permission prompts. `.tmp/` is pre-approved, stays with project context, and auto-cleans on deletion.

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

## CRITICAL: NEVER Deploy Frontend Locally

**NEVER build and deploy the frontend locally to S3.** This has caused repeated authentication outages.

**Why:** Local builds use stale/wrong `VITE_COGNITO_*` environment variables, causing auth to silently fail.

**The only safe way:** Use the CI/CD pipeline - it reads Cognito config from Terraform outputs.

**Emergency local deploy (LAST RESORT):** Read config from Terraform first:
```bash
cd infra/terraform
AWS_PROFILE=bmx-staging terraform output -json | jq '{pool_id: .cognito_user_pool_id.value, client_id: .cognito_client_id.value}'
```
Then set all `VITE_*` vars and use `npm run build:validate` before deploying.

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

## Infrastructure as Code (Terraform)

**ALL infrastructure MUST be managed via Terraform.** No manual AWS console changes.

See [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md) for:
- Detailed Terraform style requirements and workflows
- Module structure and design principles
- Validation testing (destroy/apply)
- Pipeline enforcement and drift detection

### Essential Rules

1. **NEVER** create/modify AWS resources manually
2. **ALWAYS** add infrastructure changes to `infra/terraform/`
3. **DOCUMENT** any emergency manual fixes and create issue to terraformize

### Quick Commands

```bash
cd infra/terraform
terraform fmt -recursive                                         # Format
terraform validate                                                # Validate
AWS_PROFILE=bmx-staging terraform plan -var-file=envs/staging.tfvars   # Plan
AWS_PROFILE=bmx-staging terraform apply -var-file=envs/staging.tfvars  # Apply
```

## Troubleshooting

See [docs/OPERATIONS.md](docs/OPERATIONS.md) for full troubleshooting runbook.

**Quick diagnostic:**
```bash
curl -s https://staging.api.bluemoxon.com/api/v1/health/deep | jq
```

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
