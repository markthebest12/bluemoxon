# Design: Enable Stricter TypeScript-ESLint Rules

**Issue:** #625
**Date:** 2025-12-28
**Status:** Approved

## Summary

Enable two high-value type-aware ESLint rules to catch async bugs at lint time.

## Rules to Enable

```js
"@typescript-eslint/no-floating-promises": "error"
"@typescript-eslint/no-misused-promises": "error"
```

| Rule | Catches | Example Bug |
|------|---------|-------------|
| `no-floating-promises` | Forgotten await | `fetchData()` instead of `await fetchData()` |
| `no-misused-promises` | Promise in condition | `if (fetchData())` instead of `if (await fetchData())` |

## Out of Scope (for follow-up)

- `require-await` - lower value, more false positives
- Type safety rules (`no-unsafe-assignment`, etc.)
- Consistency rules (`consistent-type-imports`, etc.)

## Implementation

### ESLint Config Changes

Update `frontend/eslint.config.js` to enable type-aware linting:

```js
{
  files: ["**/*.{ts,tsx,vue}"],
  languageOptions: {
    parserOptions: {
      project: "./tsconfig.app.json",
      tsconfigRootDir: import.meta.dirname,
    },
  },
  rules: {
    "@typescript-eslint/no-floating-promises": "error",
    "@typescript-eslint/no-misused-promises": "error",
  },
}
```

### Fix Patterns

| Violation | Fix |
|-----------|-----|
| Floating promise | Add `await` |
| Intentional fire-and-forget | Add `void` prefix |
| Promise in event handler | Use `void handler()` or wrap |

### Vue Event Handlers

If excessive false positives in Vue `@click` handlers, consider:

```js
"@typescript-eslint/no-misused-promises": [
  "error",
  { "checksVoidReturn": { "attributes": false } }
]
```

Assess after seeing violations.

## Validation

1. `npm run lint` - no violations
2. `npm run type-check` - passes
3. `npm run build` - succeeds
4. CI passes on PR

## Workflow

```
feat/eslint-stricter-rules → PR to staging → validate → PR to main
```
