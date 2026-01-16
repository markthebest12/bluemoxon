# API Compatibility Quick Reference

> Full rationale: [ADR-001](adr/001-api-compatibility-policy.md)

## TL;DR

- **Adding optional fields = SAFE** (do it anytime)
- **Removing/renaming/changing types = BREAKING** (needs new version)

## Safe Changes (v1)

| Change | Example |
|--------|---------|
| Add optional response field | `by_condition` in `DashboardResponse` |
| Add new endpoint | `GET /api/v1/reports` |
| Add query parameter (with default) | `?include_archived=false` |
| Add enum value | Add `ARCHIVED` to `BookStatus` |
| Make required field optional | `title` required → optional |

## Breaking Changes (needs v2)

| Change | Example |
|--------|---------|
| Remove field | Delete `status` from response |
| Rename field | `status` → `state` |
| Change field type | `count: int` → `count: str` |
| Add required field | New field without default value |
| Remove enum value | Remove `PENDING` from options |

## Checklist Before Merging

When modifying API schemas:

- [ ] Adding fields? Ensure they have default values
- [ ] Removing fields? **STOP** - this is breaking
- [ ] Renaming fields? **STOP** - this is breaking
- [ ] Changing types? **STOP** - this is breaking

## Client Contract

Clients consuming our API should:

- Ignore unknown fields in responses
- NOT use `additionalProperties: false` in schema validation
- Expect response schemas to grow over time
