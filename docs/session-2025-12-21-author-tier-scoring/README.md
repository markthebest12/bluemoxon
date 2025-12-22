# Session: Author Tier Scoring Alignment (#528)

**Date:** 2025-12-21
**Issue:** [#528](https://github.com/markthebest12/bluemoxon/issues/528)
**Status:** Design complete, ready for implementation

---

## Background

User noticed book 521 (Darwin's "Power of Movement in Plants") shows "Charles Darwin - not a priority author" despite Darwin being a TOP PRIORITY for 2026 acquisition goals.

**Root cause:** All authors have `priority_score: 0` - no author priorities configured.

**Reference docs:**
- `~/projects/book-collection/documentation/Victorian_Book_Acquisition_Guide.md`
- `~/projects/book-collection/documentation/January_2026_Acquisition_Targets.md`

---

## Design Decisions (via brainstorming skill)

### Author Tier System (NEW)
- 3-tier system matching publisher/binder pattern
- TIER_1: +15 points (Darwin, Lyell)
- TIER_2: +10 points (Dickens, Collins)
- TIER_3: +5 points (Ruskin)

### Publisher Updates
- Chatto and Windus → TIER_2 (Collins secondary)
- George Allen → TIER_2 (Ruskin secondary)

### Binder Updates
- Bayntun → TIER_1 (upgrade from TIER_2)
- Leighton, Son & Hodge → TIER_1 (from null)
- Hayday → TIER_1 (create new)

---

## All Changes Summary

**Authors to update (5):**
| Author | ID | Tier |
|--------|-----|------|
| Charles Darwin | 34 | TIER_1 |
| Charles Lyell | (create) | TIER_1 |
| Charles Dickens | 250 | TIER_2 |
| W. Wilkie Collins | 335 | TIER_2 |
| John Ruskin | 260 | TIER_3 |

**Publishers to update (2):**
| Publisher | ID | Tier |
|-----------|-----|------|
| Chatto and Windus | 193 | TIER_2 |
| George Allen | 197 | TIER_2 |

**Binders to update (3):**
| Binder | ID | Tier |
|--------|-----|------|
| Bayntun | 4 | TIER_1 |
| Leighton, Son & Hodge | 27 | TIER_1 |
| Hayday | (create) | TIER_1 |

---

## Next Steps

1. Write design document to `docs/plans/2025-12-21-author-tier-scoring-design.md`
2. Commit design document
3. Ask user: "Ready to set up for implementation?"
4. Use superpowers:using-git-worktrees to create isolated workspace
5. Use superpowers:writing-plans to create detailed implementation plan
6. Use superpowers:subagent-driven-development to execute

---

## CRITICAL: Superpowers Skills (MANDATORY)

**Always use skills before any task:**
- Check if a skill applies
- Use the Skill tool to invoke it
- Follow the skill exactly

**Workflow chains:**
- New feature: brainstorming → using-git-worktrees → writing-plans → subagent-driven-development
- Completing work: verification-before-completion → finishing-a-development-branch

---

## CRITICAL: Bash Command Rules

**NEVER use these - they trigger permission prompts:**
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings (history expansion)

**ALWAYS use:**
- Simple single-line commands
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls

---

## Key Files

- **Session doc:** `docs/session-2025-12-21-author-tier-scoring/README.md`
- **Design doc:** `docs/plans/2025-12-21-author-tier-scoring-design.md`
- **Implementation plan:** `docs/plans/2025-12-21-author-tier-scoring-implementation.md`
- **Worktree:** `.worktrees/author-tier-scoring`
- **Scoring service:** `backend/app/services/scoring.py`
- **Author model:** `backend/app/models/author.py`

---

*Last updated: 2025-12-21 (Design complete, awaiting implementation)*
