# BlueMoxon (bmx) Project Instructions

## BMX API Calls

Use `bmx-api` for all BlueMoxon API calls:

```bash
bmx-api GET /books                    # List books (staging default)
bmx-api --prod GET /books             # Production
bmx-api POST /books '{"title":"..."}'
bmx-api PATCH /books/123 '{"status":"..."}'
bmx-api --text-file analysis.md PUT /books/123/analysis
bmx-api --image photo.jpg POST /books/123/images
```

Keys: `~/.bmx/staging.key` and `~/.bmx/prod.key`

## Workflow: Staging → Production

**ALL changes go through staging first.** Only exception: marketing site (`site/index.html`).

```text
Feature Branch → PR to staging → Merge → Validate → PR staging→main → Deploy
```

### For Every Change

1. Create branch: `git checkout -b <type>/<description>` (feat/, fix/, docs/, chore/)
2. Make changes
3. Run validation (see Validation section below)
4. Commit: `git commit -m "<type>: <description>"`
5. PR to staging: `gh pr create --base staging`
6. Merge to staging: `gh pr merge <n> --squash` (squash for clean history)
7. After staging merge, validate in staging environment
8. Promote: `gh pr create --base main --head staging --title "chore: Promote staging"`
9. Merge to main: `gh pr merge <n> --merge` (merge commit, NOT squash)
10. Watch deploy: `gh run watch <id> --exit-status`

### Merge Strategy

| PR Type | Strategy | Command | Why |
|---------|----------|---------|-----|
| Feature → staging | Squash | `--squash` | Clean history, one commit per feature |
| staging → main | Merge | `--merge` | Preserves commit identity, prevents drift |

**Why not squash promotions?** Squash creates new commit hashes. If staging has commits A,B,C and main gets squash-ABC, Git sees them as unrelated. Next promotion conflicts because A,B,C ≠ ABC.

### Branch Protection

| Branch | Target | Protection |
|--------|--------|------------|
| `main` | app.bluemoxon.com | PR + CI + approval |
| `staging` | staging.app.bluemoxon.com | CI only |

### Post-Deploy

Always watch deploys - CI passing doesn't guarantee deploy success:

```bash
gh run list --workflow Deploy --limit 1
gh run watch <run-id> --exit-status
```

## Validation & Linting

**Run before committing** (as separate commands, not chained):

```bash
# Backend
poetry run ruff check backend/
poetry run ruff format --check backend/

# Frontend
npm run --prefix frontend lint
npm run --prefix frontend format
npm run --prefix frontend type-check

# Documentation (when docs/ changed)
npx markdownlint-cli2 "docs/**/*.md"
```

**Prettier is separate from ESLint** - run `npm run --prefix frontend format` before commit.

**Pre-commit hooks** catch most issues: `pre-commit install`

## Project Overview

```text
bluemoxon/
├── backend/          # FastAPI + SQLAlchemy
├── frontend/         # Vue 3 + TypeScript
├── infra/terraform/  # AWS infrastructure (Terraform)
├── docs/             # Documentation
└── .github/workflows/
```

**AWS Resources:** Lambda API, S3 + CloudFront (frontend/images), RDS PostgreSQL, Cognito

**Version:** Auto-generated at deploy: `YYYY.MM.DD-<short-sha>`. Check via `X-App-Version` header or `/api/v1/health/version`.

## Infrastructure (Terraform)

**ALL infrastructure via Terraform.** No manual AWS console changes.

```bash
cd infra/terraform
AWS_PROFILE=bmx-staging terraform plan -var-file=envs/staging.tfvars
AWS_PROFILE=bmx-staging terraform apply -var-file=envs/staging.tfvars
```

**API Key for Terraform:** CI fetches automatically from Secrets Manager. For manual runs:

| Environment | Secret Path | AWS Account |
|-------------|-------------|-------------|
| Staging | `bluemoxon-staging/api-key` | bmx-staging |
| Production | `bluemoxon-prod/api-key` | bmx-prod |

```bash
export TF_VAR_api_key=$(aws secretsmanager get-secret-value --secret-id bluemoxon-staging/api-key --query SecretString --output text)
terraform apply -var-file=envs/staging.tfvars
```

**Lambda Python version** must match between Terraform runtime and deploy build image (currently 3.12).

See [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md) for details.

## Code Review Before Promotion

Before promoting staging to main, run **both** review types (belt and suspenders):

| Skill | Focus | Question |
|-------|-------|----------|
| `superpowers:requesting-code-review` | Plan compliance | "Does this do what it should?" |
| `review-changes` | Implementation flaws | "What's wrong with how I did it?" |

Prod is high-stakes — double coverage is justified. Fix all findings before merging.

## Key Constraints

| Rule | Reason |
|------|--------|
| Never deploy frontend locally | Causes auth outages - use CI/CD |
| Use `.tmp/` not `/tmp` | Keeps temp files with project context |
| Deferred work → GitHub issue | Comments get lost |
| After merge conflicts → run ruff | Catches duplicate definitions |

## Operations & Troubleshooting

See [docs/OPERATIONS.md](docs/OPERATIONS.md) for:

- Database sync (prod → staging)
- User management
- Migrations via `/health/migrate`
- Troubleshooting runbook

**Quick health check:**

```bash
curl -s https://staging.api.bluemoxon.com/api/v1/health/deep | jq
```

## Quick Reference

```bash
# Development
npm run --prefix frontend dev          # Frontend dev server
poetry run pytest                      # Backend tests

# Git/CI
gh pr create --base staging            # Create feature PR
gh pr checks <n> --watch               # Watch CI
gh pr merge <n> --squash               # Merge feature PR (squash)
gh pr merge <n> --merge                # Merge promotion PR (no squash)

# Staging
AWS_PROFILE=bmx-staging aws ...        # All staging AWS commands
```
