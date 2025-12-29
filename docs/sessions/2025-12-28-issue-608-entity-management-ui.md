# Session: Issue #608 - UI Management for Binders, Authors, Publishers

**Date:** 2025-12-28
**Issue:** [#608](https://github.com/bluemoxon/bluemoxon/issues/608)

## Objective
Create a UI management page for binders, authors, and publishers with:
- CRUD operations
- Tier designation (1, 2, 3)
- Preferred/not-preferred status for scoring criteria

## Session Log

### Phase 1: Brainstorming and Design
- Starting brainstorming to refine requirements
- Exploring current codebase for existing patterns

---

## Context Exploration

### Current State
- **Models**: Author, Publisher, Binder all have `tier` fields (TIER_1, TIER_2, TIER_3)
- **Author** has `priority_score` (int) for scoring weight
- **No "preferred" field** exists yet on any entity
- **CRUD APIs** exist for all three entities with editor role protection
- **AdminConfigView** displays entity tiers as read-only (no edit UI)
- **Scoring engine** uses tiers: Tier 1 Publisher = +25pts, Tier 1 Binder = +30pts, etc.

### Gaps to Address
1. Add "preferred" boolean field to entities
2. Build UI for editing tier and preferred status
3. Determine where this UI lives (new page vs existing admin)

## Design Decisions

1. **UI Location**: Extend existing AdminConfigView "Entity Tiers" tab with edit capabilities
2. **Preferred Scope**: All three entities (Author, Publisher, Binder) get a `preferred` boolean field
3. **Scoring Impact**: Preferred adds +10 bonus points (additive, on top of tier bonuses)
4. **Edit Pattern**: Inline editing (dropdowns/checkboxes) for tier and preferred, auto-save on change
5. **CRUD Scope**: Full CRUD + reassignment (merge duplicates by reassigning books before delete)
6. **Reassignment UX**: Pre-delete modal shows book count, dropdown to select target entity, "Reassign and Delete" button
7. **Tab Layout**: Unified view with three collapsible sections (Authors, Publishers, Binders), each with "Add" button
8. **Filtering**: Simple text search box per section to filter by name

## Implementation Progress
(To be filled during implementation)
