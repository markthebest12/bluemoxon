# Session: Lambda Pre-flight Validation

**Date:** 2026-01-19
**Issue:** Brainstorming session - Lambda deployment safety improvements
**Branch:** `feat/preflight-validation-integration`

## CRITICAL RULES FOR CONTINUATION

### Superpowers Skills - MANDATORY
**ALWAYS invoke relevant superpowers skills before ANY action.** Even 1% chance a skill applies = invoke it.

Key skills to use:
- `superpowers:brainstorming` - Before any design work
- `superpowers:writing-plans` - Before implementation
- `superpowers:test-driven-development` - For all code
- `superpowers:dispatching-parallel-agents` - For independent tasks
- `superpowers:verification-before-completion` - Before claiming done

### Bash Command Rules - NEVER VIOLATE
**NEVER use these (trigger permission prompts):**
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings

**ALWAYS use:**
- Simple single-line commands
- Separate sequential Bash tool calls instead of &&
- `bmx-api` for all BlueMoxon API calls

## Problem Statement

Lambda deployments fail because code expects environment variables, permissions, or infrastructure that doesn't exist yet. Root cause: Terraform apply is a separate manual step, not enforced before Lambda deploy.

Common failure modes:
- Code expects `BMX_NEW_QUEUE` but Terraform wasn't applied
- IAM permissions not updated for new resources
- Infrastructure (SQS queues) doesn't exist yet

## Solution Implemented

**Pre-flight validation** that runs in CI before Lambda deploy:
1. Parse `backend/app/config.py` to extract all `BMX_*` settings
2. Read actual Lambda environment variables from AWS
3. Compare expected vs actual - fail if required vars missing
4. Phase 1: Warning mode (continue-on-error: true)

## Implementation Complete

### Files Created

| File | Purpose |
|------|---------|
| `scripts/extract_config_vars.py` | Parse config.py for BMX_* settings |
| `scripts/validate_lambda_config.py` | Compare expected vs actual |
| `tests/scripts/test_extract_config_vars.py` | 13 tests |
| `tests/scripts/test_validate_lambda_config.py` | 8 tests |

### Files Modified

| File | Change |
|------|--------|
| `backend/app/config.py` | Added validation sentinel (BMX_VALIDATION_SENTINEL) |
| `infra/terraform/outputs.tf` | Added lambda_environment_variables output |
| `infra/terraform/modules/lambda/outputs.tf` | Added environment_variables output |
| `.github/workflows/deploy.yml` | Added validate-config job + API key fetch from Secrets Manager |
| `CLAUDE.md` | Documented Secrets Manager paths for API key |

### Additional Fix: API Key from Secrets Manager

**Problem:** `TF_VAR_api_key` was empty during Terraform apply (SHA256 of empty string).

**Fix:** CI now fetches API key from Secrets Manager before Terraform commands:
- Staging: `bluemoxon-staging/api-key`
- Production: `bluemoxon-prod/api-key`

**Documentation added (by user):** `docs/INFRASTRUCTURE.md` - API Keys section:
- Storage locations (7 places keys must be synced)
- Authentication flow
- Rotation process
- Verification commands
- Common issues troubleshooting

### Parallel Execution Summary

Used 4 parallel agents in separate worktrees:
- Group A: Extract script (6 commits, 13 tests)
- Group B: Validate script (6 commits, 8 tests)
- Group C: Sentinel setting (1 commit)
- Group D: Terraform output (1 commit)

All merged into `feat/preflight-validation-integration` branch.

## Code Review Fixes

After code review, the following issues were identified and fixed:

| Issue | Fix |
|-------|-----|
| Sentinel breaks local dev | Removed from production config.py (tests already prove validation works) |
| Shell injection in workflow | Write JSON to temp file, use `--actual-file` instead of shell arg |
| Field mismatch (line vs source) | Changed extract to output `source: "config.py:LINE"` format |
| Missing Optional[str] support | Added handling for `Optional[X]` and `Union[X, None]` in AST parser |
| Silent failure on first deploy | Added explicit warning when Lambda doesn't exist |
| Empty values pass validation | Added check for empty string values on required vars |
| Hardcoded Terraform lines | Removed specific line numbers from error message |
| API key in job outputs | Removed from outputs (only used within configure job) |
| sys.path manipulation | Moved to conftest.py |
| Brittle relative paths | Added pytest fixtures for paths |

### Files Modified in Code Review Fixes

| File | Change |
|------|--------|
| `backend/app/config.py` | Removed validation sentinel |
| `.github/workflows/deploy.yml` | Fixed shell injection, first deploy handling, API key output |
| `scripts/extract_config_vars.py` | Changed `line` to `source` field, added Optional[str] support |
| `scripts/validate_lambda_config.py` | Added empty value check, `--actual-file` option, fixed error message |
| `conftest.py` | Added scripts directory to path |
| `tests/scripts/conftest.py` | Created with path fixtures |
| `tests/scripts/test_extract_config_vars.py` | Updated for source field, added Optional[str] tests |
| `tests/scripts/test_validate_lambda_config.py` | Updated to use fixtures, added empty value test |

## Current Status

- [x] Design approved
- [x] Implementation complete
- [x] All 24 tests passing (up from 21)
- [x] Workflow integration done
- [x] Worktrees cleaned up
- [x] PR to staging: https://github.com/markthebest12/bluemoxon/pull/1189
- [x] Code review fixes implemented
- [ ] Push code review fixes
- [ ] Merge PR #1189 to staging (awaiting review)

## Next Steps

1. **Push code review fixes** - commit and push to branch

2. **Review and merge PR #1189** (user review required)

3. **After staging merge** - verify validation runs and passes in deploy logs
   - Note: Sentinel removed, so no deliberate warning expected
   - Validation should PASS (all vars exist in Lambda)

4. **Phase 2** - Monitor for false positives, tune if needed

5. **Phase 3** - Enable blocking mode (remove continue-on-error)

## Design Documents

- `docs/plans/2026-01-19-lambda-preflight-validation-design.md` - Approved design
- `docs/plans/2026-01-19-lambda-preflight-validation-plan.md` - Implementation plan

## Related

- Issue #1140 (async worker checklist) - completed earlier in this session
