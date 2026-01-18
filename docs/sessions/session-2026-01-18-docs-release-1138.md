# Session: Documentation for v2026.01.XX Release

**Date:** 2026-01-18
**Issue:** #1138
**Status:** IN PROGRESS

## Critical Rules for Continuation

### 1. ALWAYS Use Superpowers Skills
| Stage | Skill | When |
|-------|-------|------|
| Planning | `superpowers:brainstorming` | Before starting work |
| Implementation | `superpowers:test-driven-development` | Before writing code |
| Debugging | `superpowers:systematic-debugging` | ANY bug/issue |
| Before completion | `superpowers:verification-before-completion` | Before claiming done |
| Code review | `superpowers:receiving-code-review` | When getting feedback |

### 2. Bash Command Rules - NEVER Use These
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings

### 3. ALWAYS Use Instead
- Simple single-line commands
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls

### 4. PR Review Required
- Before going to staging: User review required
- Before going to prod: User review required

## Task Overview

Document new features since v2026.01.07 for the next dot release.

## Documentation Areas

### 1. docs/FEATURES.md - User-facing features
- [ ] Collection Spotlight
- [ ] Interactive Dashboard Charts
- [ ] Victorian Dark Mode
- [ ] Era Filter
- [ ] Condition Grade Dropdown
- [ ] Auto-parse Publication Dates
- [ ] Entity Validation
- [ ] Entity Management UI
- [ ] Real-time Exchange Rates
- [ ] CSV Export Improvements
- [ ] Carrier API Support
- [ ] Garbage Image Detection
- [ ] Auto-process Book Images
- [ ] Redis Dashboard Caching

### 2. site/ - Marketing Website
- [ ] Collection Spotlight feature
- [ ] Interactive Charts
- [ ] Dark Mode showcase
- [ ] AI Image Processing

### 3. docs/INFRASTRUCTURE.md - Infrastructure changes
- [ ] Lambda Layers
- [ ] Cleanup Lambda
- [ ] Tracking worker redesign
- [ ] ElastiCache Redis
- [ ] Artifacts bucket
- [ ] Path-based deploy filtering

## Progress

(To be updated as work progresses)
