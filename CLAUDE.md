# BlueMoxon (bmx) Project Instructions

## CRITICAL: CI/CD Workflow Requirements

**NEVER push directly to main.** All changes MUST go through the CI/CD pipeline:

### Required Workflow for ALL Code Changes

```bash
# 1. Create feature branch (use conventional naming)
git checkout -b <type>/<description>
# Types: feat/, fix/, refactor/, docs/, chore/, perf/

# 2. Make changes

# 3. Run local validation BEFORE committing (REQUIRED)
cd backend && poetry run ruff check . && poetry run ruff format --check .
cd frontend && npm run lint && npm run type-check

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

## Branching Strategy (GitFlow)

```
main ─────●─────●─────●─────→  [Production: app.bluemoxon.com]
           \     \     \
staging ────●─────●─────●────→  [Staging: staging.app.bluemoxon.com] (planned)
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
# Standard feature → main (production)
git checkout -b feat/my-feature
# ... make changes ...
gh pr create --base main

# Feature → staging for testing
git checkout -b feat/experimental
# ... make changes ...
gh pr create --base staging   # PRs to staging, not main

# Promote staging to production
gh pr create --base main --head staging --title "chore: Promote staging to production"
```

## Version System

Application version is tracked in `/VERSION` file at the project root.

### Version Visibility
| Location | How to Check |
|----------|--------------|
| API Response Header | `X-App-Version` header on ALL responses |
| API Endpoint | `GET /api/v1/health/version` |
| Frontend Config | `import { APP_VERSION } from '@/config'` |
| Deploy Info | `GET /api/v1/health/info` (includes git SHA, deploy time) |

### Updating Version
```bash
# Edit VERSION file (e.g., 1.0.0 → 1.1.0)
echo "1.1.0" > VERSION
git add VERSION
git commit -m "chore: Bump version to 1.1.0"
```

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

**Use `.tmp/` for all temporary files** instead of `/tmp`:
```bash
.tmp/                  # Project-local temp directory (gitignored)
```

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
- **Auth**: Cognito User Pool

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
