# Refactor Batch Plan

Issue batch covering frontend Vue refactors and backend API fixes/refactors.

## Phase 1: Frontend (4 issues → 3 PRs)

| Order | PR | Issues | Description |
|-------|-----|--------|-------------|
| 1 | Type Safety | #853 + #854 | Replace `ref<any[]>` with proper types; extract shared constants |
| 2 | Error Handling | #855 | Fix silent error handling (empty catch blocks) |
| 3 | Component Split | #856 | Split BookDetailView.vue god component |

## Phase 2: Backend Fixes (3 issues → 3 PRs)

| Order | PR | Issues | Description |
|-------|-----|--------|-------------|
| 4 | Currency Rates | #861 | Fix hardcoded 2024 exchange rates |
| 5 | Pagination | #862 | Fix broken pagination for combined scope |
| 6 | Images Module | #866 + #858 | Fix silent thumbnail failure + async/sync I/O |

## Phase 3: Backend Refactors (4 issues → 4 PRs)

| Order | PR | Issues | Description |
|-------|-----|--------|-------------|
| 7 | Books Module | #863 + #864 | list_books params validation + stale job dedup |
| 8 | Stats | #859 | Decimal→float conversion cleanup |
| 9 | Users | #860 | Cognito client singleton |
| 10 | Error Patterns | #865 | Unify error handling across routers |

## Rationale

- **Frontend first**: Already working on Vue issues; complete that context before switching
- **Type safety before component split**: Cleaner code when splitting BookDetailView.vue
- **User-facing fixes prioritized**: #861 (stale currency rates) and #862 (broken pagination) affect users now
- **Group by file**: images.py (#866 + #858) and books.py (#863 + #864) touched once each
- **Error patterns last**: Cross-cutting refactor easier after individual files stabilize
