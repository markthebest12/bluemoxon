# Prompting Guide for Claude Sessions

## Why This Matters

Claude sessions start fresh with no memory of previous work. Without proper context:
- Claude may skip established patterns
- Work may not align with existing design docs
- Validation steps get missed
- GitHub issues don't get updated

## Prompt Template

Use this template when starting work on a tracked task:

```
## Task
[One sentence: what you want done]

## References
- GitHub Issue: #[number]
- Design Doc: docs/plans/[filename]-design.md
- Implementation Plan: docs/plans/[filename]-implementation.md (if exists)

## Current State
- Phase: [X of Y]
- Last completed: [task/phase]
- Branch: [branch name if applicable]

## Expected Outcome
- [ ] [Specific deliverable 1]
- [ ] [Specific deliverable 2]
- [ ] Validation: [how to verify it works]

## Constraints
- Follow TDD (test first)
- Update GitHub issue when done
- Don't mark complete until validated
```

## Examples

### Starting a New Phase

```
## Task
Implement Phase 1 (Binder Tier Migration) of the analysis enrichment design.

## References
- GitHub Issue: #237
- Design Doc: docs/plans/2025-12-13-analysis-enrichment-design.md
- Implementation Plan: docs/plans/2025-12-13-analysis-enrichment-implementation.md

## Current State
- Phase: 1 of 6
- Last completed: Design approved
- Branch: feature/analysis-enrichment (in worktree)

## Expected Outcome
- [ ] Alembic migration adds `tier` column to binders table
- [ ] Binder model updated with tier field
- [ ] Tier 1/2 binders seeded in migration
- [ ] Validation: `bmx-api GET /binders` shows tier values

## Constraints
- Follow TDD (test first)
- Update GitHub issue #237 when phase complete
- Run migration in staging before marking done
```

### Continuing Mid-Phase

```
## Task
Continue Phase 2 (Scoring Enhancement) - left off at Task 2.3.

## References
- GitHub Issue: #237
- Implementation Plan: docs/plans/2025-12-13-analysis-enrichment-implementation.md

## Current State
- Phase: 2 of 6, Task 2.3
- Last completed: Task 2.2 (added binder_tier parameter to calculate_strategic_fit)
- Branch: feature/analysis-enrichment

## Expected Outcome
- [ ] Complete Task 2.3: Add DOUBLE TIER 1 bonus logic
- [ ] Complete Task 2.4: Update books.py to pass binder_tier
- [ ] All scoring tests pass
- [ ] Validation: Book 501 strategic_fit increases

## Constraints
- Check implementation plan for exact code snippets
- Run `poetry run pytest tests/test_scoring.py` after each task
```

### Bug Fix with Validation

```
## Task
Fix and validate the price display bug in acquisitions view.

## References
- GitHub Issue: #236
- Fix already committed (needs validation)

## Current State
- Code fix applied to formatPrice/formatDiscount
- Not yet deployed to staging
- Not yet validated by user

## Expected Outcome
- [ ] Push to staging branch
- [ ] Deploy to staging environment
- [ ] Manual test: "Paid: $142.41" displays correctly (not "Paid: -")
- [ ] Manual test: "30% off" displays correctly (not "- off")
- [ ] Update issue #236 with test results
- [ ] Close issue only after user confirms

## Constraints
- Don't close issue until user validates
- Consider adding Playwright test for regression
```

## Key Principles

### 1. Always Reference Documentation
- Design docs explain WHY decisions were made
- Implementation docs have exact code snippets
- GitHub issues track progress and blockers

### 2. State Current Position
- Which phase/task are we on?
- What was last completed?
- What branch are we working in?

### 3. Define "Done" Explicitly
- What files should be changed?
- What tests should pass?
- How do we validate it works?
- Who needs to approve/test?

### 4. Remind About Process
- TDD: Write tests first
- Commit incrementally
- Update GitHub issues
- Don't claim "done" without validation

## Anti-Patterns to Avoid

| Bad Prompt | Why It Fails | Better Prompt |
|------------|--------------|---------------|
| "Fix the scoring bug" | No context, no references | "Fix #237 per design doc, Phase 2, Task 2.3" |
| "Continue where we left off" | Claude has no memory | "Continue Phase 2, Task 2.3 (last: added binder_tier param)" |
| "Make it work" | No success criteria | "Validation: Book 501 score reaches ~215" |
| "Do all 6 phases" | Too broad, will lose focus | "Implement Phase 1, then report back" |

## Staging & Production Workflows

### Deploy to Staging

```
## Task
Deploy [feature/fix] to staging for validation.

## References
- GitHub Issue: #[number]
- Branch: [branch name]

## Pre-Deploy Checklist
- [ ] All tests pass locally
- [ ] Code reviewed/approved
- [ ] No lint errors

## Expected Outcome
- [ ] PR merged to `staging` branch
- [ ] CI passes
- [ ] Deployed to staging.app.bluemoxon.com
- [ ] Smoke test: [specific endpoint/page to check]

## Validation Steps
1. Check API: `bmx-api GET /[endpoint]`
2. Check UI: https://staging.app.bluemoxon.com/[page]
3. Test specific flow: [describe user journey]

## After Validation
- Update GitHub issue with staging test results
- If passing, prepare promotion PR to main
- If failing, document issues and fix
```

### Promote Staging to Production

```
## Task
Promote validated changes from staging to production.

## References
- GitHub Issue: #[number]
- Staging validation: [link to issue comment or test results]

## Pre-Promotion Checklist
- [ ] Staging tests passed (documented in issue)
- [ ] User accepted changes in staging
- [ ] No breaking changes to API contracts
- [ ] Database migrations are backward-compatible

## Steps
1. Create PR: staging → main
2. Title: "chore: Promote staging to production - [feature summary]"
3. Body: Link to GitHub issues being closed
4. Wait for CI to pass
5. Merge (auto-deploys to production)

## Post-Deploy Validation
- [ ] Check: https://api.bluemoxon.com/api/v1/health/deep
- [ ] Check: https://app.bluemoxon.com/[affected page]
- [ ] Verify: [specific functionality works]
- [ ] Watch deploy workflow: `gh run watch <id> --exit-status`

## After Production Deploy
- Close GitHub issues with "Deployed to production, validated"
- Update any documentation if needed
```

### Hotfix to Production

```
## Task
Emergency fix for production issue.

## References
- GitHub Issue: #[number] (create if doesn't exist)
- Severity: [Critical/High]

## Current Impact
- What's broken: [description]
- Users affected: [scope]

## Fix Strategy
- [ ] Create fix branch from `main` (not staging)
- [ ] Minimal change only - no refactoring
- [ ] Test locally
- [ ] PR directly to `main` with "hotfix:" prefix

## Validation (expedited)
- [ ] CI passes
- [ ] Quick smoke test of fix
- [ ] Deploy and verify in production
- [ ] Backport fix to staging branch

## Post-Hotfix
- Document root cause in GitHub issue
- Create follow-up issue if broader fix needed
- Update staging to include fix
```

### Database Migration Deployment

```
## Task
Deploy database migration to [staging/production].

## References
- Migration file: backend/alembic/versions/[filename].py
- GitHub Issue: #[number]

## Pre-Migration Checklist
- [ ] Migration tested locally with SQLite
- [ ] Migration is backward-compatible (no breaking changes)
- [ ] Rollback tested: `alembic downgrade -1`

## Deploy Steps
1. Deploy code with migration to target environment
2. Run migration via health endpoint:
   - Staging: `curl -X POST https://staging.api.bluemoxon.com/api/v1/health/migrate`
   - Production: `curl -X POST https://api.bluemoxon.com/api/v1/health/migrate`
3. Verify migration applied: Check logs or query new table/column

## Validation
- [ ] Migration endpoint returns success
- [ ] New schema accessible via API
- [ ] Existing data preserved
- [ ] Application functions normally

## Rollback Plan (if needed)
- Migrations should be backward-compatible
- If critical failure: revert code deploy, run downgrade
```

---

## Parallel Infrastructure Work

Infrastructure issues (#224-235) can run in parallel with feature work. Use these prompts to weave them in.

### Check Infrastructure Status

```
## Task
Review current infrastructure issue status before starting session.

## References
- Epic: #229 (Terraform parity)
- Issues: #224-235

## Quick Status Check
Run: `gh issue list --label infra --state open`

## Questions to Answer
1. Are any infra issues blocking feature work?
2. Are any infra issues quick wins (< 30 min)?
3. Should we tackle an infra issue before/after today's feature work?
```

### Interleave Infrastructure Task

```
## Task
Complete infrastructure issue #[number] between feature phases.

## References
- GitHub Issue: #[number]
- Epic: #229
- Blocking: [list any issues this unblocks]

## Context
- Currently working on: [feature name]
- Good breakpoint: [between Phase X and Y]
- Time estimate: [X minutes]

## Expected Outcome
- [ ] Terraform changes applied to staging
- [ ] Validated with `terraform plan` shows no drift
- [ ] GitHub issue updated/closed

## Return To
After completing, return to [feature], Phase [X], Task [Y]
```

### Terraform Import Session

```
## Task
Import existing AWS resource into Terraform (#224/#225/#226).

## References
- GitHub Issue: #[number]
- Resource type: [Cognito/Lambda/RDS]
- Design doc: docs/INFRASTRUCTURE_GOVERNANCE.md

## Pre-Import Checklist
- [ ] Resource exists in AWS
- [ ] Terraform module ready to receive import
- [ ] Backup/snapshot taken (if applicable)

## Import Steps
1. Get resource ID from AWS console/CLI
2. Run import: `terraform import 'module.X.resource.Y' <aws-id>`
3. Run plan: `terraform plan -var-file=envs/staging.tfvars`
4. Adjust Terraform config until plan shows no changes
5. Commit .tf changes

## Validation
- [ ] `terraform plan` shows "No changes"
- [ ] Resource still functions correctly
- [ ] Update epic #229 progress

## Risk Mitigation
- Import does NOT change AWS resources
- If something goes wrong: `terraform state rm` removes from state only
- Always test in staging before production
```

### End-of-Session Infrastructure Check

```
## Task
Quick infrastructure hygiene before ending session.

## Questions
1. Did any feature work create resources that should be in Terraform?
2. Are there any quick infra issues that could be done in 15 min?
3. Should drift detection be run? `gh workflow run drift-detection.yml`

## If Time Permits (< 15 min tasks)
- Update CLAUDE.md with new infrastructure values
- Close completed infra issues
- Update epic #229 with progress
```

---

## Session Handoff

When ending a session, ask Claude to generate a handoff summary:

```
Generate a handoff summary for the next Claude session, including:
1. What was completed this session
2. Current phase/task position
3. Any blockers or decisions needed
4. Next steps with file references
```

This summary should be added to the GitHub issue or a session notes file.
