# ADR-001: API Compatibility Policy

## Status

Accepted

## Date

2026-01-10

## Context

Adding `by_condition` and `by_category` fields to `DashboardResponse` in #965 raised questions about API compatibility. Specifically:

1. **Pydantic behavior:** By default, Pydantic is additive - clients receive extra fields without errors
2. **Potential issue:** Clients using strict schema validation (`additionalProperties: false` in OpenAPI codegen) would reject new fields
3. **No existing policy:** We had no documented guidelines for what constitutes a breaking change

We needed clear rules for the team to follow when evolving the API.

## Decision

We adopt a **moderate compatibility policy** aligned with industry standards (similar to protobuf/GraphQL evolution rules).

### Breaking Changes (require new API version)

| Change Type | Example | Why Breaking |
|-------------|---------|--------------|
| Remove field | Delete `status` from response | Clients relying on field will fail |
| Rename field | `status` → `state` | Same as removal from client perspective |
| Change type | `count: number` → `count: string` | Type coercion failures |
| Add required field | New field without default | Old requests missing field will fail |
| Remove enum value | Remove `PENDING` from status | Clients sending that value will fail |

### Non-Breaking Changes (safe within v1)

| Change Type | Example | Why Safe |
|-------------|---------|----------|
| Add optional field | New `by_condition` in response | Clients ignore unknown fields |
| Add enum value | Add `ARCHIVED` to status | Existing values still work |
| Add endpoint | New `/api/v1/reports` route | No impact on existing endpoints |
| Relax validation | Required → optional | Old requests still valid |
| Add query param | New `?include_deleted=true` | Defaults maintain old behavior |

### Client Expectations

- Clients SHOULD ignore unknown fields in responses
- Clients SHOULD NOT use `additionalProperties: false` in schema validation
- Response schemas may grow over time within a major version

### Versioning Strategy (Deferred)

We currently use URL-based versioning (`/api/v1`). When breaking changes are needed, we will decide between:

- **URL-based:** `/api/v2` (simple, visible)
- **Header-based:** `Accept: application/vnd.bmx.v2+json` (single URL)

This decision is deferred until we actually need v2, following YAGNI principles.

## Consequences

### Positive

- Team has clear guidelines for safe API evolution
- Can add features without coordinating version bumps
- Aligns with industry best practices

### Negative

- Clients using strict validation may break (documented as client responsibility)
- Cannot remove/rename fields without version bump

### Neutral

- v2 decision deferred - will revisit when needed

## References

- Issue: #1003
- Triggering PR: #965 (dashboard charts)
- Google API Design Guide: https://cloud.google.com/apis/design/compatibility
- Stripe API Versioning: https://stripe.com/docs/api/versioning
