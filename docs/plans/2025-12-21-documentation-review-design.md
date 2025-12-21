# Documentation Review & Improvement Design

**Date:** 2025-12-21
**Status:** In Progress

## Overview

Comprehensive review and restructuring of BlueMoxon documentation to improve discoverability, fill gaps, eliminate redundancy, and clean up stale content.

## Primary Audiences

1. **Operations/Support** - Runbooks, troubleshooting, monitoring, API examples
2. **Developer Onboarding** - Architecture understanding, component connections, getting started (both AI assistants and human developers)

## Pain Point Priority

1. **Discoverability** - Information exists but hard to find
2. **Missing critical info** - Key procedures/decisions not documented
3. **Redundancy/conflicts** - Same info in multiple places, sometimes contradicting
4. **Staleness** - Outdated references, orphaned content

## Scope

Full stack review:
- Backend (API endpoints, services, models, integrations)
- Infrastructure (Terraform modules, resources, CI/CD pipelines)
- Frontend (components, views, state management)
- Scripts (utilities, automation)
- Scraper (extraction logic)
- Prompts (AI prompts and purposes)

## Navigation Architecture

Three-tier hybrid structure:

```
docs/
├── INDEX.md                    # Master index - "start here"
├── OPERATIONS.md               # Hub: runbooks, troubleshooting, monitoring
├── ARCHITECTURE.md             # Hub: system design, decisions, diagrams
├── DEVELOPMENT.md              # Hub: local setup, workflows, testing
├── api/
│   └── README.md               # API domain docs + links
├── infrastructure/
│   └── README.md               # Infra domain docs + links
└── ...
```

**Principles:**
- Every doc reachable within 2 clicks from INDEX.md
- No orphan documents
- CLAUDE.md becomes cheat sheet with links, not comprehensive manual

## Review Phases

### Phase 1: Documentation Inventory
- Catalog every doc: location, purpose, last modified, audience
- Map cross-references
- Flag duplicates, orphans, conflicts, stale content
- Output: `session-2025-12-21-documentation-review/inventory.md`

### Phase 2: Code Feature Audit
- Systematic walk through each codebase area
- Note features, identify missing docs, capture diagram needs
- Output: `session-2025-12-21-documentation-review/feature-audit.md`

### Phase 3: Gap Analysis & Consolidation Plan
- Cross-reference inventory vs. feature audit
- Identify: new docs needed, diagrams needed, consolidations, deletions
- Output: `session-2025-12-21-documentation-review/gap-analysis.md`

### Phase 4: Execution
- Create new docs and diagrams
- Consolidate redundancies
- Build INDEX.md and hub documents
- Slim down CLAUDE.md
- Archive obsolete content

## Diagram Standards

| Type | Purpose | Location |
|------|---------|----------|
| Architecture (C4-style) | System context, containers, components | ARCHITECTURE.md |
| Flow diagrams | Request flows, analysis pipeline, image processing | Feature-specific docs |
| Sequence diagrams | API call chains, Bedrock retry logic, async job flow | OPERATIONS.md, API docs |
| Infrastructure | AWS resources, VPC layout, CI/CD pipeline | INFRASTRUCTURE.md |

## Operational Content Standards

Each procedure includes:
- **Purpose**: Why you'd run this
- **Prerequisites**: What you need (AWS profile, permissions)
- **Command example**: Copy-pasteable with expected output
- **Troubleshooting**: Common failures and fixes
- **Related**: Links to deeper docs

## API Documentation Standards

Each endpoint includes:
- Method + path
- Purpose (one line)
- Request/response examples (curl + JSON)
- Error codes and meanings
- Related endpoints

## Cleanup Rules

### CLAUDE.md
- Keep: Quick command references, permission patterns, critical workflow rules
- Move out: Detailed procedures, architecture details, troubleshooting guides
- Target: Under 20KB (currently 36KB)

### Redundancy
- Pick canonical location based on audience
- Other locations get one-line summary + link

### Orphans
- Code referenced but doesn't exist → GitHub issue
- Code exists but undocumented → Document or flag for removal
- Docs referencing removed features → Archive or delete

### Plans Directory
- Keep: Recent/relevant plans (last 30 days)
- Archive: Completed plans older than 30 days
- Delete: Abandoned/superseded plans

## GitHub Issues

Create issues for discovered:
- Unfinished implementations (stubs, TODOs)
- Missing features that docs reference
- Infrastructure gaps or inconsistencies
- Code that should be deprecated/removed

## Deliverables

1. `docs/INDEX.md` - Master navigation
2. Updated hub docs (OPERATIONS.md, ARCHITECTURE.md, DEVELOPMENT.md)
3. Directory READMEs where needed
4. New/updated Mermaid diagrams
5. Slimmed CLAUDE.md with links
6. Archived obsolete docs
7. GitHub issues for improvements discovered

## Definition of Done

- [ ] Every doc reachable within 2 clicks from INDEX.md
- [ ] No orphan documents
- [ ] No undocumented major features
- [ ] Key operational procedures have runbook-style docs
- [ ] CLAUDE.md under 20KB
