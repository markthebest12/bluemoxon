# ESLint 9 Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate frontend from ESLint 8.x to ESLint 9 with flat config format.

**Architecture:** Replace legacy `.eslintrc.cjs` with modern `eslint.config.js` using flat config. Update to typescript-eslint v8 and eslint-plugin-vue v9.32+ for native ESLint 9 support.

**Tech Stack:** ESLint 9.17.0, typescript-eslint 8.19.0, eslint-plugin-vue 9.32.0, eslint-config-prettier 10.0.1

**Design Doc:** `docs/plans/2025-12-28-eslint9-migration-design.md`

---

## Task 1: Update package.json Dependencies

**Files:**

- Modify: `frontend/package.json`

**Step 1: Remove old packages from devDependencies**

Remove these lines from `devDependencies`:

```json
"@rushstack/eslint-patch": "^1.3.3",
"@vue/eslint-config-prettier": "^10.2.0",
"@vue/eslint-config-typescript": "^13.0.0",
"eslint": "^8.49.0",
"eslint-plugin-vue": "^9.17.0",
```

**Step 2: Add new packages to devDependencies**

Add these lines to `devDependencies`:

```json
"@eslint/js": "^9.17.0",
"eslint": "^9.17.0",
"eslint-config-prettier": "^10.0.1",
"eslint-plugin-vue": "^9.32.0",
"globals": "^15.14.0",
"typescript-eslint": "^8.19.0",
```

**Step 3: Run npm install**

Run: `npm --prefix frontend install`
Expected: Packages install without errors

**Step 4: Commit package changes**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: update ESLint dependencies for v9 migration"
```

---

## Task 2: Create New Flat Config File

**Files:**

- Create: `frontend/eslint.config.js`

**Step 1: Create the new config file**

Create `frontend/eslint.config.js` with this content:

```javascript
import js from "@eslint/js";
import typescript from "typescript-eslint";
import vue from "eslint-plugin-vue";
import prettier from "eslint-config-prettier";
import globals from "globals";

export default [
  // Base JS recommended rules
  js.configs.recommended,

  // TypeScript recommended rules
  ...typescript.configs.recommended,

  // Vue 3 essential rules
  ...vue.configs["flat/essential"],

  // Project-specific configuration
  {
    files: ["**/*.{js,ts,vue}"],
    languageOptions: {
      ecmaVersion: "latest",
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      // Allow unused vars prefixed with _
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      // Allow any for now (can tighten later)
      "@typescript-eslint/no-explicit-any": "off",
      // Vue component naming
      "vue/multi-word-component-names": "off",
    },
  },

  // Prettier must be last - disables conflicting rules
  prettier,
];
```

**Step 2: Commit new config**

```bash
git add frontend/eslint.config.js
git commit -m "feat: add ESLint 9 flat config"
```

---

## Task 3: Delete Legacy Config File

**Files:**

- Delete: `frontend/.eslintrc.cjs`

**Step 1: Remove the old config file**

Run: `rm frontend/.eslintrc.cjs`

**Step 2: Commit deletion**

```bash
git add frontend/.eslintrc.cjs
git commit -m "chore: remove legacy .eslintrc.cjs"
```

---

## Task 4: Update Lint Script in package.json

**Files:**

- Modify: `frontend/package.json`

**Step 1: Check current lint script**

The current lint script uses `--ext` and `--ignore-path` which are deprecated in ESLint 9.
Old: `"lint": "eslint . --ext .vue,.js,.jsx,.cjs,.mjs,.ts,.tsx,.cts,.mts --fix --ignore-path .gitignore"`

**Step 2: Update to ESLint 9 syntax**

Change the lint script to:

```json
"lint": "eslint . --fix"
```

ESLint 9 flat config:

- Auto-detects file types from config
- Uses .gitignore by default when no ignores specified
- No need for `--ext` flag

**Step 3: Commit script update**

```bash
git add frontend/package.json
git commit -m "chore: simplify lint script for ESLint 9"
```

---

## Task 5: Verify Migration Works

**Files:**

- None (verification only)

**Step 1: Run lint**

Run: `npm --prefix frontend run lint`
Expected: No errors (may have warnings for unused vars)

**Step 2: Run type-check**

Run: `npm --prefix frontend run type-check`
Expected: No errors

**Step 3: Run build**

Run: `npm --prefix frontend run build`
Expected: Build completes successfully

**Step 4: Test lint catches violations**

Create temporary test file `frontend/src/lint-test.ts`:

```typescript
const unusedVar = "test";
```

Run: `npm --prefix frontend run lint`
Expected: Warning for unused variable (not prefixed with _)

Delete test file: `rm frontend/src/lint-test.ts`

---

## Task 6: Final Cleanup and Commit

**Files:**

- None (just verification)

**Step 1: Verify no uncommitted changes**

Run: `git status`
Expected: Clean working directory

**Step 2: Run full verification suite**

Run these in sequence:

- `npm --prefix frontend run lint`
- `npm --prefix frontend run type-check`
- `npm --prefix frontend run build`

All should pass.

---

## Verification Checklist

- [ ] `npm run lint` passes
- [ ] `npm run type-check` passes
- [ ] `npm run build` passes
- [ ] Unused var without `_` prefix triggers warning
- [ ] Unused var with `_` prefix is ignored
- [ ] All commits have conventional commit messages

---

## Notes for PR Review

When creating PR:

1. Target: `staging` branch
2. Title: `chore: migrate to ESLint 9 with flat config`
3. Body should reference:
   - Issue #567
   - Design doc: `docs/plans/2025-12-28-eslint9-migration-design.md`
   - Note that Dependabot PR #317 should be closed (superseded by this)
