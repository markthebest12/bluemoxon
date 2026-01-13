# CRITICAL: READ THIS BEFORE ANY CODE CHANGES

## YOU MUST FOLLOW THE STAGING-FIRST WORKFLOW

On 2026-01-11, Claude pushed directly to main without going through staging.
This violated the fundamental CI/CD requirements and deployed untested code to production.

**THIS MUST NEVER HAPPEN AGAIN.**

## Required Workflow for ALL Code Changes

```
Feature Branch → Staging → Production
       ↓             ↓          ↓
    PR to staging  Deploy   PR staging→main
                   + Test      Deploy
```

### Step-by-Step (NO EXCEPTIONS)

1. **Create feature branch** (NEVER commit on main or staging)
   ```bash
   git checkout staging
   git pull
   git checkout -b feat/your-feature
   ```

2. **Make changes and commit**
   ```bash
   git add -A
   git commit -m "feat: description"
   ```

3. **Push and create PR to STAGING** (NOT main!)
   ```bash
   git push -u origin feat/your-feature
   gh pr create --base staging --title "feat: description"
   ```

4. **Wait for CI to pass**
   ```bash
   gh pr checks <pr-number> --watch
   ```

5. **Merge to staging**
   ```bash
   gh pr merge <pr-number> --squash --delete-branch
   ```

6. **Validate in staging environment**
   - Check https://staging.app.bluemoxon.com
   - Verify the changes work as expected

7. **Create PR from staging to main**
   ```bash
   gh pr create --base main --head staging --title "chore: Promote staging to production"
   ```

8. **Merge to main after CI passes**
   ```bash
   gh pr merge <pr-number> --squash
   ```

## NEVER DO THESE

- `git push origin main` - BLOCKED by pre-push hook
- `git push origin staging` - BLOCKED by pre-push hook
- Committing directly on main or staging branches
- Skipping staging "because it's a small change"
- Using `--no-verify` without explicit user approval

## If You Catch Yourself About to Push to Main

STOP. Ask yourself:
1. Did I create a feature branch?
2. Did I PR to staging first?
3. Did I validate in staging?
4. Did I PR from staging to main?

If any answer is NO, you are about to repeat the 2026-01-11 failure.
