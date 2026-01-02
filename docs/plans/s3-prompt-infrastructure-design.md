# S3 Prompt Infrastructure Design

**Issue:** #747
**Status:** Future - Placeholder for design phase

## Problem

Prompts are embedded in Python code. Refinement requires code releases.

## Proposed Solution

Store prompts as S3 objects with versioning.

## Open Questions

1. Latency - S3 fetch vs embedded strings (caching strategy?)
2. Drift - Prompts changing without code review
3. Troubleshooting - Which prompt version was used for a given analysis?
4. Rollback - How to revert to previous prompt version?
5. Testing - How to test prompt changes before production?

## Files Affected

- `backend/app/services/eval_generation.py`
- `backend/app/services/bedrock.py`
- `backend/app/services/listing.py`
- `backend/app/services/fmv_lookup.py`

## Design

*To be completed during brainstorming session*
