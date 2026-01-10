# Session Log: Query Consolidation + Caching (#1001 + #1002)

**Date:** 2026-01-09
**Issues:** #1001 (Query consolidation), #1002 (Caching layer)

## Context

### Issue #1001 - Query Consolidation
Dashboard endpoint makes 10+ separate database queries per request. Proposal: use PostgreSQL GROUPING SETS to fetch multiple aggregations in single query.

### Issue #1002 - Caching Layer
No caching currently - every request hits DB. Options:
- A: Redis TTL cache (recommended in issue)
- B: Materialized View
- C: In-memory stale-while-revalidate

### Current Implementation (`backend/app/api/v1/stats.py`)
The `/dashboard` endpoint calls 8 functions, each with their own queries:
1. `get_overview()` - ~6 queries (counts, values, volumes, authenticated, in_transit, week_delta)
2. `get_bindings()` - 1 query
3. `get_by_era()` - 1 query
4. `get_by_publisher()` - 1 query
5. `get_by_author()` - 2 queries (aggregation + batch sample titles)
6. `get_by_condition()` - 1 query
7. `get_by_category()` - 1 query
8. `get_acquisitions_daily()` - 1 query

Total: **~14 queries per dashboard load**

---

## Brainstorming Session

### Questions & Decisions

**Q1: Which issue first?**
- Decision: **#1001 (Query consolidation) first**
- Rationale: No infrastructure changes, easier to test, makes caching more valuable later

**Q2: Consolidation scope?**
- Decision: **Moderate consolidation**
- Consolidate: condition + category + era into 1 GROUPING SETS query
- Consolidate: overview stats into 1-2 queries
- Keep separate: by_author, by_publisher, bindings, acquisitions_daily
- Target: 14 → ~6 queries (57% reduction)

**Q3: Code structure?**
- Decision: **Dashboard-only optimization**
- New consolidated queries only for `/dashboard` endpoint
- Individual endpoints (`/by-condition`, etc.) unchanged
- Rationale: Dashboard is the hot path, simpler implementation, no API breaking changes

**Q4: Testing approach?**
- Decision: **Parallel execution** during refactor
- Run old and new queries, assert equality
- Keep property-based tests after refactor for ongoing regression
- TDD: write comparison test first, then implement

