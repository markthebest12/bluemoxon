# AI-Powered Unrelated Image Detection - Session Resume

**Issue:** #487
**Date:** 2025-12-20
**Status:** Implementation complete, awaiting staging validation

## Summary

Implemented AI-powered detection and removal of unrelated images (seller ads, logos, different books) from eBay imports by extending the existing Claude Vision analysis in the Eval Runbook generation flow.

## Completed Tasks (1-5)

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Extended Claude Vision prompt with IMAGE RELEVANCE detection | `575c6a3` |
| 2 | Added `unrelated_images` and `unrelated_reasons` to all return dicts | `7dd363f` |
| 3 | Created `backend/app/services/image_cleanup.py` with `delete_unrelated_images()` | `79eabd2` |
| 4 | Integrated cleanup into `generate_eval_runbook()` after AI analysis | `19c4b05` |
| 5 | Added 8 unit tests in `backend/tests/services/test_image_cleanup.py` | `7b7ffb1` |
| - | Fixed formatting issues | `9367ef6` |

## Current State

- **All code is complete and committed to staging branch**
- **CI passed** - Deploy workflow run `20399753124` was in progress (at "Deploy to staging" step)
- **Awaiting:** Staging deploy completion and manual validation (Task 6)

## Remaining Tasks (6-7)

### Task 6: Manual Validation on Staging

```bash
# Check deploy completed
gh run list --workflow Deploy --limit 1

# Test on book 506 (known to have unrelated images 17-23)
bmx-api POST /books/506/evaluate

# Check CloudWatch logs for unrelated image detection
AWS_PROFILE=bmx-staging aws logs filter-log-events --log-group-name /aws/lambda/bluemoxon-staging-api --filter-pattern "unrelated" --limit 20

# Verify images were deleted
bmx-api GET /books/506
```

### Task 7: Create PR and Deploy to Production

```bash
gh pr create --base main --head staging --title "feat: AI-powered unrelated image detection (#487)"
gh pr checks <pr-number> --watch
gh pr merge <pr-number> --squash --delete-branch
gh run watch <deploy-run-id> --exit-status
```

## Key Files Modified

1. `backend/app/services/eval_generation.py` - Extended Claude prompt, integrated cleanup
2. `backend/app/services/image_cleanup.py` - New service for S3/DB image deletion
3. `backend/tests/services/test_image_cleanup.py` - 8 unit tests

## Design Documents

- Design: `docs/plans/2025-12-20-ai-unrelated-image-detection-design.md`
- Implementation Plan: `docs/plans/2025-12-20-ai-unrelated-image-detection-implementation.md`

## How It Works

1. During eval runbook generation, Claude Vision analyzes book images
2. Prompt now asks Claude to identify images that are NOT the listed book
3. Claude returns `unrelated_images: [17, 18, 19]` and `unrelated_reasons: {...}`
4. `delete_unrelated_images()` removes flagged images from S3 and database
5. Remaining images are reordered

## Resume Instructions

```
Continue implementing AI-powered unrelated image detection for issue #487.

Current state:
- Tasks 1-5 complete (code, tests committed to staging)
- Deploy to staging was in progress (run 20399753124)
- Need to: complete Task 6 (manual validation) and Task 7 (PR to production)

Plan file: docs/plans/2025-12-20-ai-unrelated-image-detection-implementation.md

Use superpowers:subagent-driven-development to continue from Task 6.
```
