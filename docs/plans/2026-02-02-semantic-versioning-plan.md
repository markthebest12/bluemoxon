# Semantic Versioning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace date-based versioning with Uplift-powered semantic versioning, add PR title validation, and show version in the nav bar.

**Architecture:** Uplift runs on push to main, analyzes conventional commits, bumps `backend/pyproject.toml`, creates annotated tags. Production deploys trigger on tag push (`v*`). Staging deploys continue on push to `staging`. PR titles are validated via GitHub Action.

**Tech Stack:** Uplift v2.26.0, GitHub Actions, Vue 3, Vite

---

### Task 1: Create `.uplift.yml`

**Files:**
- Create: `.uplift.yml`

**Step 1: Create the Uplift config file**

```yaml
bumps:
  - file: backend/pyproject.toml
    regex:
      - pattern: 'version\s*=\s*".*"'
        semver: true

changelog:
  include:
    - feat
    - fix
    - perf
    - refactor

commitAuthor:
  name: uplift-bot
  email: uplift-bot@users.noreply.github.com

commitMessage: 'ci(release): v${VERSION}'

annotatedTags: true
```

**Step 2: Commit**

```bash
git add .uplift.yml
git commit -m "feat: add Uplift configuration for semantic versioning"
```

---

### Task 2: Create `.github/workflows/release.yml`

**Files:**
- Create: `.github/workflows/release.yml`

**Step 1: Create the release workflow**

```yaml
name: Release

on:
  push:
    branches: [main]

jobs:
  release:
    runs-on: ubuntu-latest
    # Skip if this is an Uplift release commit
    if: "!startsWith(github.event.head_commit.message, 'ci(release):')"
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0
          token: ${{ secrets.PAT }}

      - name: Release
        uses: gembaadvantage/uplift-action@0d28005618a55f97d0bb9253329383720d3e9031 # v2
        with:
          args: release
          version: 'v2.26.0'
        env:
          GITHUB_TOKEN: ${{ secrets.PAT }}
```

**Step 2: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "feat: add Uplift release workflow"
```

---

### Task 3: Create `.github/workflows/pr-title.yml`

**Files:**
- Create: `.github/workflows/pr-title.yml`

**Step 1: Create the PR title validation workflow**

```yaml
name: PR Title

on:
  pull_request_target:
    types: [opened, edited, synchronize]
    branches: [staging, main]

permissions:
  pull-requests: read

jobs:
  validate:
    name: Validate PR Title
    runs-on: ubuntu-latest
    steps:
      - uses: amannn/action-semantic-pull-request@48f256284bd46cdaab1048c3721360e808335d50 # v6.1.1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          types: |
            feat
            fix
            perf
            refactor
            docs
            chore
            ci
            test
            style
            build
          requireScope: false
```

**Step 2: Commit**

```bash
git add .github/workflows/pr-title.yml
git commit -m "feat: add PR title conventional commit validation"
```

---

### Task 4: Update `backend/pyproject.toml` version

**Files:**
- Modify: `backend/pyproject.toml:3`

**Step 1: Update version from `0.1.0` to `3.0.1`**

Change line 3:
```
version = "0.1.0"
```
to:
```
version = "3.0.1"
```

**Step 2: Commit**

```bash
git add backend/pyproject.toml
git commit -m "chore: set version to 3.0.1 for semver bootstrap"
```

---

### Task 5: Update `deploy.yml` — triggers and environment detection

**Files:**
- Modify: `.github/workflows/deploy.yml`

This is the largest task. Multiple sections of deploy.yml need to change.

**Step 1: Update file header comment (lines 1-9)**

Replace:
```yaml
# Deploy Pipeline - Deploys to staging/production based on branch
# Uses AWS OIDC for secure, keyless authentication
#
# Workflow:
#   push to staging → deploy to staging environment
#   push to main    → deploy to production environment
#
# PERFORMANCE: Lambda deploys run in parallel after layer is published
# This reduces deploy time from ~7min to ~3-4min
```

With:
```yaml
# Deploy Pipeline - Deploys to staging/production
# Uses AWS OIDC for secure, keyless authentication
#
# Workflow:
#   push to staging  → deploy to staging environment
#   tag push (v*)    → deploy to production environment
#
# Production deploys are triggered by Uplift creating a semver tag on main.
# See .github/workflows/release.yml for the Uplift workflow.
#
# PERFORMANCE: Lambda deploys run in parallel after layer is published
# This reduces deploy time from ~7min to ~3-4min
```

**Step 2: Update triggers (lines 13-19)**

Replace:
```yaml
on:
  push:
    branches: [main, staging]
    paths-ignore:
      - '**.md'
      - 'docs/**'
      - '.github/dependabot.yml'
      - 'LICENSE'
      - '.gitignore'
```

With:
```yaml
on:
  push:
    branches: [staging]
    tags: ['v*']
    paths-ignore:
      - '**.md'
      - 'docs/**'
      - '.github/dependabot.yml'
      - 'LICENSE'
      - '.gitignore'
```

**Step 3: Update environment detection in configure job (lines 142-154)**

Replace:
```yaml
      - name: Determine environment
        id: env
        run: |
          if [[ "${{ github.ref_name }}" == "main" ]]; then
            echo "environment=production" >> $GITHUB_OUTPUT
            echo "tf_backend_file=backends/prod.hcl" >> $GITHUB_OUTPUT
          elif [[ "${{ github.ref_name }}" == "staging" ]]; then
            echo "environment=staging" >> $GITHUB_OUTPUT
            echo "tf_backend_file=backends/staging.hcl" >> $GITHUB_OUTPUT
          else
            echo "ERROR: Unknown branch ${{ github.ref_name }}"
            exit 1
          fi
```

With:
```yaml
      - name: Determine environment
        id: env
        run: |
          if [[ "${{ github.ref }}" == refs/tags/v* ]]; then
            echo "environment=production" >> $GITHUB_OUTPUT
            echo "tf_backend_file=backends/prod.hcl" >> $GITHUB_OUTPUT
          elif [[ "${{ github.ref_name }}" == "staging" ]]; then
            echo "environment=staging" >> $GITHUB_OUTPUT
            echo "tf_backend_file=backends/staging.hcl" >> $GITHUB_OUTPUT
          else
            echo "ERROR: Unknown ref ${{ github.ref }}"
            exit 1
          fi
```

**Step 4: Update generate-version job (lines 426-445)**

Replace the entire `generate-version` job:
```yaml
  generate-version:
    name: Generate Version
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.version }}
      short_sha: ${{ steps.version.outputs.short_sha }}
      deployed_at: ${{ steps.version.outputs.deployed_at }}
    steps:
      - name: Generate version string
        id: version
        run: |
          DATE=$(date -u +%Y.%m.%d)
          SHORT_SHA=${GITHUB_SHA::7}
          VERSION="${DATE}-${SHORT_SHA}"
          DEPLOYED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

          echo "Generated version: $VERSION"
          echo "version=$VERSION" >> $GITHUB_OUTPUT
          echo "short_sha=$SHORT_SHA" >> $GITHUB_OUTPUT
          echo "deployed_at=$DEPLOYED_AT" >> $GITHUB_OUTPUT
```

With:
```yaml
  generate-version:
    name: Generate Version
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.version }}
      short_sha: ${{ steps.version.outputs.short_sha }}
      deployed_at: ${{ steps.version.outputs.deployed_at }}
    steps:
      - uses: actions/checkout@v6
        with:
          sparse-checkout: backend/pyproject.toml
          sparse-checkout-cone-mode: false

      - name: Generate version string
        id: version
        run: |
          SHORT_SHA=${GITHUB_SHA::7}
          DEPLOYED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

          if [[ "${{ github.ref }}" == refs/tags/v* ]]; then
            # Production: extract semver from tag (strip 'v' prefix)
            VERSION="${GITHUB_REF_NAME#v}"
          else
            # Staging: read from pyproject.toml + build metadata
            PYPROJECT_VERSION=$(grep -oP 'version\s*=\s*"\K[^"]+' backend/pyproject.toml)
            VERSION="${PYPROJECT_VERSION}+${SHORT_SHA}"
          fi

          echo "Generated version: $VERSION"
          echo "version=$VERSION" >> $GITHUB_OUTPUT
          echo "short_sha=$SHORT_SHA" >> $GITHUB_OUTPUT
          echo "deployed_at=$DEPLOYED_AT" >> $GITHUB_OUTPUT
```

**Step 5: Force full deploy on tag pushes**

The `changes` job uses `dorny/paths-filter` which won't work for tag pushes (no branch diff). Add an output to signal tag pushes as full deploys.

Add a new output to the `changes` job after the existing outputs (around line 75):
```yaml
      is_tag: ${{ steps.check-tag.outputs.is_tag }}
```

Add a new step before the `Detect changed paths` step:
```yaml
      - name: Check if tag push
        id: check-tag
        run: |
          if [[ "${{ github.ref }}" == refs/tags/v* ]]; then
            echo "is_tag=true" >> $GITHUB_OUTPUT
          else
            echo "is_tag=false" >> $GITHUB_OUTPUT
          fi
```

Then update **every** `if` condition that references `needs.changes.outputs.*` to also check for tag pushes. For example, change:

```yaml
if: needs.changes.outputs.backend == 'true' || github.event.inputs.force_full_deploy == 'true'
```

To:
```yaml
if: needs.changes.outputs.backend == 'true' || github.event.inputs.force_full_deploy == 'true' || needs.changes.outputs.is_tag == 'true'
```

Apply this pattern to ALL lines that check `needs.changes.outputs`:
- Lines: 458, 514, 584, 642, 679, 723, 763, 821, 951, 1097, 1164, 1251, 1327

For multi-line conditions (like line 642 for scraper), maintain the same format:
```yaml
    if: >-
      needs.configure.outputs.environment != '' &&
      (needs.changes.outputs.scraper == 'true' || github.event.inputs.force_full_deploy == 'true' || needs.changes.outputs.is_tag == 'true')
```

**Step 6: Remove `create-release` job (lines 1806-1834)**

Delete the entire section:
```yaml
  # ============================================
  # Create Release Tag (production only)
  # ============================================

  create-release:
    name: Create Release Tag
    runs-on: ubuntu-latest
    needs: [configure, smoke-test]
    if: needs.configure.outputs.environment == 'production'

    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: Create release tag
        run: |
          VERSION="v$(date -u '+%Y.%m.%d')-$(echo ${{ github.sha }} | head -c 7)"

          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

          git tag -a "$VERSION" -m "Release $VERSION

          Deployed at: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
          Commit: ${{ github.sha }}"

          git push origin "$VERSION"
          echo "Release tag created: $VERSION"
```

Also remove `create-release` from any `needs:` arrays in subsequent jobs.

**Step 7: Update permissions comment (line 47-50)**

Replace:
```yaml
# Required for AWS OIDC authentication, release tagging, and drift issues
permissions:
  id-token: write
  contents: write  # Required for creating release tags
```

With:
```yaml
# Required for AWS OIDC authentication and drift issues
permissions:
  id-token: write
  contents: write  # Required for drift issue management
```

**Step 8: Remove APP_VERSION env var comment (line 44-45)**

Replace:
```yaml
  # Auto-generated version: YYYY.MM.DD-<short-sha>
  APP_VERSION: ""  # Set dynamically in generate-version job
```

With:
```yaml
  # Semver from tag (production) or pyproject.toml+sha (staging)
  APP_VERSION: ""  # Set dynamically in generate-version job
```

**Step 9: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "feat: switch deploy triggers to tag-based production releases"
```

---

### Task 6: Add version display to NavBar

**Files:**
- Modify: `frontend/src/components/layout/NavBar.vue`

**Step 1: Import APP_VERSION in the script section**

Add after line 5 (`import ThemeToggle from "@/components/ui/ThemeToggle.vue";`):

```typescript
import { APP_VERSION } from "@/config";
```

**Step 2: Add version to bottom of desktop nav area**

The NavBar is a horizontal top bar, not a sidebar. The "bottom of sidebar" intent translates to a subtle version indicator. Add it in the desktop navigation area next to the logo.

After the closing `</div>` of the desktop nav container (after line 188, before the Mobile Menu section), add the version display as a bottom bar:

Actually, the cleanest placement for a horizontal navbar is: add a small version text at the far-left bottom of the mobile menu, and for desktop, add it to the user dropdown. But the user specifically said "bottom of sidebar" — and this is a top navbar, not a sidebar.

The best equivalent: add a subtle `v3.0.1` next to the logo on the left side of the nav bar.

After the logo `<RouterLink>` (line 48-50), add:

```html
        <span class="text-xs text-victorian-paper-cream/40 hidden md:inline ml-2 self-center">v{{ appVersion }}</span>
```

And in the script setup, add a computed:
```typescript
const appVersion = APP_VERSION;
```

For mobile: add version at the very bottom of the mobile menu, after the Sign Out button / Sign In link, before the closing `</div>` of the mobile menu container (before line 273):

```html
        <span class="block text-xs text-victorian-paper-cream/30 text-center pt-3 border-t border-victorian-hunter-700 mt-1">v{{ appVersion }}</span>
```

**Step 3: Verify locally**

```bash
npm run --prefix frontend dev
```

Open browser, confirm version appears next to logo (desktop) and at bottom of mobile menu.

**Step 4: Lint check**

```bash
npm run --prefix frontend lint
npm run --prefix frontend format
npm run --prefix frontend type-check
```

**Step 5: Commit**

```bash
git add frontend/src/components/layout/NavBar.vue
git commit -m "feat: display app version in navigation bar"
```

---

### Task 7: Update CLAUDE.md version reference

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update version documentation**

Find the line:
```
**Version:** Auto-generated at deploy: `YYYY.MM.DD-<short-sha>`. Check via `X-App-Version` header or `/api/v1/health/version`.
```

Replace with:
```
**Version:** Semantic versioning via [Uplift](https://upliftci.dev/). Production deploys trigger on tag push (`v*`). Check via `/api/v1/health/version`.
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update version documentation for semver"
```

---

### Task 8: Final validation and PR

**Step 1: Run all linting**

```bash
poetry run ruff check backend/
poetry run ruff format --check backend/
npm run --prefix frontend lint
npm run --prefix frontend format
npm run --prefix frontend type-check
```

**Step 2: Create PR to staging**

```bash
gh pr create --base staging --title "feat: implement semantic versioning with Uplift" --body "$(cat <<'EOF'
## Summary

Implements tagged semantic versioning with Uplift (#1589):

- Add `.uplift.yml` for automated version bumping of `backend/pyproject.toml`
- Add release workflow (runs Uplift on push to main)
- Add PR title validation (conventional commits enforcement)
- Update deploy triggers: staging on branch push, production on tag push (`v*`)
- Remove old `create-release` job (Uplift handles tagging)
- Display version in nav bar (desktop: next to logo, mobile: bottom of menu)
- Bootstrap version at `3.0.1`

## Manual steps after merge to main

1. Add `PAT` secret to GitHub repo settings (Uplift needs it to push past branch protection)
2. Tag current main HEAD: `git tag v3.0.1 && git push origin v3.0.1`
3. Add `Validate PR Title` as required status check in branch protection settings

Closes #1589

## Test plan

- [ ] Verify PR title validation blocks PRs with bad titles
- [ ] Verify version displays in nav bar (desktop and mobile)
- [ ] After merge to main + tagging, verify Uplift creates first release
- [ ] Verify staging deploy still works on push to staging
- [ ] Verify production deploy triggers on tag push

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
