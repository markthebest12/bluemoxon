# Napoleon Analysis Re-run Session

**Date:** 2025-12-31
**Status:** IN PROGRESS - Design phase for fix

## CRITICAL REMINDERS

### Superpowers Skills - MANDATORY
**If there is even a 1% chance a skill might apply, you MUST invoke the skill.**
- Use `superpowers:brainstorming` before any creative/feature work
- Use `superpowers:systematic-debugging` before proposing fixes
- Use `superpowers:verification-before-completion` before claiming work is done
- Check skill applicability BEFORE any response or action

### Bash Command Rules - STRICT
**NEVER use (triggers permission prompts):**
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings

**ALWAYS use:**
- Simple single-line commands
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls (no permission prompts)

---

## Background

### Original Issue
Napoleon publisher books in production have incomplete analyses due to what was initially thought to be Bedrock throttling. 124 books had `recommendations` field as `null`.

### Root Cause Investigation
After re-running several batches (books 1-4, 21-27, 33, 41, 47, etc.), discovered **100% failure rate** - ALL re-run analyses still had null recommendations.

**Key Finding:** The problem is NOT Bedrock throttling. It's **output token exhaustion**.

### Root Cause Identified
1. `max_tokens=16000` in `bedrock.py:409` allows ~60K chars output
2. Napoleon prompt requests 12+ sections totaling 500-700+ lines
3. Model generates sections 1-4 in detail (~50K chars) but exhausts tokens before Section 12
4. "Conclusions and Recommendations" section is NEVER generated
5. Parser correctly looks for `## 12. Conclusions and Recommendations` but it doesn't exist
6. Claude Sonnet 4.5 supports up to **64K output tokens** - we're only using 16K

**Evidence:**
- Book 554: Bedrock returned 63,487 chars, but `recommendations` still null
- Raw markdown ends mid-sentence at "David Copperfield, or" - truncated
- `grep -c "Conclusions"` on raw markdown returns 0 - section never generated
- Code never checks `stop_reason` from Bedrock response

---

## Approved Design (via Brainstorming Skill)

### Backend Changes

**1. Increase max_tokens (bedrock.py:409)**
```python
# Change from 16000 to 32000
max_tokens: int = 32000
```

**2. Add stop_reason logging (bedrock.py:463-467)**
```python
response_body = json.loads(response["body"].read())
stop_reason = response_body.get("stop_reason", "unknown")
result_text = response_body["content"][0]["text"]

logger.info(f"Bedrock returned {len(result_text)} chars, stop_reason={stop_reason}")
if stop_reason == "max_tokens":
    logger.warning(f"Output truncated - hit max_tokens limit")
```

**3. Add analysis_issues to book list API response**
```python
analysis_issues = []
if book.analysis:
    if book.analysis.recommendations is None:
        analysis_issues.append("truncated")
    if book.analysis.extraction_status == "degraded":
        analysis_issues.append("degraded")
    if book.analysis.condition_assessment is None:
        analysis_issues.append("missing_condition")
    if book.analysis.market_analysis is None:
        analysis_issues.append("missing_market")
```

### Frontend Changes

**1. Add analysis_issues to book type**
```typescript
analysis_issues?: string[] | null;
```

**2. Warning icon placement (TWO locations)**
- Next to "View Analysis" link
- On the book card itself (badge/indicator)

**3. Icon style:** Amber/yellow warning triangle

**4. Tooltip content (technical):**
```typescript
function formatAnalysisIssues(issues: string[]): string {
  const labels: Record<string, string> = {
    truncated: "Truncated: recommendations section missing",
    degraded: "Degraded: fallback extraction used",
    missing_condition: "Missing: condition assessment",
    missing_market: "Missing: market analysis",
  };
  return issues.map(i => labels[i] || i).join("\n");
}
```

---

## Next Steps

### Immediate (before resuming re-runs)
1. **Implement backend changes:**
   - Update `max_tokens` to 32000 in `backend/app/services/bedrock.py:409`
   - Add `stop_reason` logging in `invoke_bedrock()` function
   - Add `analysis_issues` field to book list serialization

2. **Implement frontend changes:**
   - Add `analysis_issues` to book type
   - Add warning icon next to "View Analysis" in AcquisitionsView.vue
   - Add warning icon/badge on book card
   - Add tooltip with technical issue details

3. **Deploy to staging and test**

4. **Deploy to production**

### After fix deployed
5. **Re-run all 124 incomplete Napoleon analyses** with new max_tokens limit
6. **Verify recommendations section now appears** in re-run analyses

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/services/bedrock.py` | max_tokens=32000, add stop_reason logging |
| `backend/app/api/v1/books.py` | Add analysis_issues to book serialization |
| `backend/app/schemas/book.py` | Add analysis_issues field to schema |
| `frontend/src/types/book.ts` | Add analysis_issues to Book interface |
| `frontend/src/views/AcquisitionsView.vue` | Add warning icons (3 card layouts) |
| `frontend/src/views/BookDetailView.vue` | Add warning icon near View Analysis button |

---

## Books Status

### DO NOT RE-RUN YET - Fix must be deployed first

### 124 Books with NULL Recommendations (incomplete):
```
1, 2, 3, 4, 21, 22, 23, 24, 25, 26, 27, 33, 41, 47, 51, 53, 56, 57, 58, 60,
62, 63, 64, 65, 66, 67, 68, 335, 336, 337, 340, 341, 342, 343, 345, 346, 347,
348, 350, 351, 352, 366, 367, 372, 374, 375, 377, 378, 379, 380, 381, 382, 383,
384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399,
400, 401, 402, 403, 404, 405, 488, 489, 493, 494, 496, 497, 498, 500, 502, 503,
504, 505, 509, 512, 514, 515, 517, 520, 525, 527, 528, 531, 533, 535, 539, 540,
541, 542, 544, 545, 547, 548, 549, 550, 554, 555, 556, 557, 559, 560, 561, 562,
563, 564, 565, 566, 567, 568, 569, 570
```

### Special Notes:
- **DO NOT touch book 373** (user explicit instruction)
- Book 22 has stale "failed" job status - needs job cleared before retry
- Books 51, 53 failed with "Input is too long" (12 images each) - separate issue

---

## Cost Impact

| Aspect | Current (16K) | Proposed (32K) |
|--------|---------------|----------------|
| Output chars | ~60K | ~100-120K |
| Bedrock cost | ~$0.12/analysis | ~$0.20/analysis |
| Generation time | ~3-4 min | ~5-6 min |
| All sections complete | No | Yes |
