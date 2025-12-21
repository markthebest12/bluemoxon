# Gap Analysis & Consolidation Plan

**Generated:** 2025-12-21
**Status:** Complete

## Summary

Cross-referencing documentation inventory with code feature audit to create actionable execution plan.

| Category | Count |
|----------|-------|
| New Documents Needed | 5 |
| Diagrams Needed | 12 |
| Documents to Consolidate | 8 |
| Documents to Archive | 15+ |
| Terraform READMEs Missing | 5 |

---

## 1. New Documents Needed

### Priority 1: Operations Hub

**File:** `docs/OPERATIONS.md`
**Purpose:** Runbook-style operations documentation
**Audience:** Operations/Support

**Content to include:**
- Health check procedures (from health.py endpoints)
- Database migration runbook
- Prod→Staging sync procedures
- Troubleshooting guide (from CLAUDE.md)
- Monitoring/alerting overview
- Emergency procedures

**Sources:**
- CLAUDE.md troubleshooting section
- feature-audit.md health.py section
- DATABASE_SYNC.md (link to)
- sync-prod-to-staging.sh documentation

---

### Priority 2: Prompts Documentation

**File:** `docs/PROMPTS.md` (or expand BEDROCK.md)
**Purpose:** AI prompt documentation
**Audience:** Developers

**Content to include:**
- Napoleon Framework overview
- STRUCTURED-DATA block format
- Condition grade standards (ABAA)
- Binder identification tiers
- Metadata block parsing
- Field extraction logic

**Sources:**
- prompts/napoleon-framework/v2.md
- feature-audit.md Napoleon section
- AnalysisViewer.vue stripping logic

---

### Priority 3: Master Index

**File:** `docs/INDEX.md`
**Purpose:** Navigation hub - "start here"
**Audience:** All

**Structure:**
```markdown
# BlueMoxon Documentation

## Quick Start
- [Development Setup](DEVELOPMENT.md)
- [Architecture Overview](ARCHITECTURE.md)

## For Operations
- [Operations Runbook](OPERATIONS.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Rollback Procedures](ROLLBACK.md)

## For Developers
- [API Reference](API_REFERENCE.md)
- [Database Schema](DATABASE.md)
- [Bedrock/AI Integration](BEDROCK.md)
- [Infrastructure Guide](INFRASTRUCTURE.md)

## Reference
- [Features Catalog](FEATURES.md)
- [CI/CD Pipeline](CI_CD.md)
```

---

### Priority 4: Scraper Documentation

**File:** `scraper/README.md`
**Purpose:** Container Lambda documentation
**Audience:** Developers

**Content to include:**
- Architecture overview
- Container build process
- ECR deployment
- Rate limiting handling
- Warmup scheduling
- Local testing

**Sources:**
- feature-audit.md scraper section
- scraper/handler.py
- infra/terraform/modules/scraper-lambda/

---

### Priority 5: Design System Documentation

**File:** `docs/DESIGN_SYSTEM.md` or add to FEATURES.md
**Purpose:** Victorian design system reference
**Audience:** Developers

**Content to include:**
- Color palette (Victorian colors)
- Typography
- Component patterns
- Chart.js color schemes
- Print stylesheet considerations

**Sources:**
- StatisticsDashboard.vue chartColors
- tailwind.config.js (if customized)
- Print CSS from InsuranceReportView

---

## 2. Diagrams Needed

### High Priority (Operations)

| Diagram | Type | Location | Purpose |
|---------|------|----------|---------|
| Bedrock retry/backoff | Sequence | BEDROCK.md | Troubleshooting |
| SQS worker job flow | Sequence | OPERATIONS.md | Job monitoring |
| Async job architecture | Component | INFRASTRUCTURE.md | Architecture understanding |

### High Priority (Developer)

| Diagram | Type | Location | Purpose |
|---------|------|----------|---------|
| eBay listing import pipeline | Flow | FEATURES.md | Feature understanding |
| Eval runbook generation | Flow | FEATURES.md | Feature understanding |
| FMV lookup process | Flow | FEATURES.md | Feature understanding |
| Auth flow (login → MFA → dashboard) | Flow | FEATURES.md | Auth understanding |

### Medium Priority

| Diagram | Type | Location | Purpose |
|---------|------|----------|---------|
| Scoring engine data flow | Component | FEATURES.md | Onboarding |
| Acquisitions workflow (Kanban) | Flow | FEATURES.md | Feature understanding |
| Scraper container build/deploy | Flow | scraper/README.md | CI/CD understanding |
| Lambda + VPC + RDS | Architecture | INFRASTRUCTURE.md | Infrastructure overview |
| Victorian design system | Component | DESIGN_SYSTEM.md | Design reference |

---

## 3. Documents to Consolidate

### CLAUDE.md Reduction (36KB → <20KB)

**Move to OPERATIONS.md:**
- Troubleshooting section (~50 lines)
- Health check procedures

**Move to DEPLOYMENT.md:**
- Staging-first workflow section (~60 lines)
- Deploy configuration details

**Move to CI_CD.md:**
- Branching strategy section (~40 lines)
- CI/CD workflow requirements (~80 lines)

**Move to INFRASTRUCTURE.md:**
- Terraform guidelines section (~200 lines)
- AWS resources section (~20 lines)

**Move to DATABASE.md:**
- Database migrations section (~20 lines)

**Keep in CLAUDE.md:**
- Bash command formatting rules
- BMX API call examples
- Permission pattern guidelines
- Quick commands reference
- Project structure overview
- Version system
- Token-saving guidelines
- Critical rules (never deploy frontend locally, etc.)

**Estimated reduction:** ~470 lines moved → ~520 lines remaining (~19KB)

---

### API.md + API_REFERENCE.md Merge

**Current state:**
- API.md: ~140 lines, outdated
- API_REFERENCE.md: ~335 lines, incomplete

**Action:** Merge into single `API_REFERENCE.md`
- Delete stale content from API.md
- Add missing endpoints from feature-audit.md
- Add request/response examples

**Missing endpoints to add:**
- `/health/live`, `/health/ready`, `/health/deep`, `/health/info`, `/health/version`
- `/health/migrate`, `/health/cleanup-orphans`
- `/listings/extract`, `/listings/extract-async`, `/listings/extract/{item_id}/status`
- `/eval-runbooks`, `/eval-runbooks/price`, `/eval-runbooks/history`, `/eval-runbooks/refresh`

---

### Deployment Documentation

**Current state:**
- DEPLOYMENT.md: ~300 lines
- CI_CD.md: ~285 lines
- Overlap in deploy procedures

**Action:** Keep separate but clarify purposes
- DEPLOYMENT.md: Manual deployment, rollback procedures
- CI_CD.md: Pipeline configuration, GitHub Actions
- Remove duplicate procedures

---

## 4. Documents to Archive

### Plans Directory Cleanup

**Archive (move to `docs/archive/plans/`):**

| Document | Age | Reason |
|----------|-----|--------|
| 2024-12-09-victorian-ui-design.md | >30 days | Implemented |
| 2025-12-08-cognito-sync-implementation.md | >30 days | Implemented |
| 2025-12-08-frontend-config-drift-design.md | >30 days | Implemented |
| 2025-12-08-staging-auth-investigation.md | >30 days | Debug notes |
| 2025-12-08-terraform-conformance-review.md | >30 days | Completed |
| 2025-12-09-sequence-reset-design.md | >30 days | DB fix completed |
| All implementation docs | Various | Reference only |

**Keep in plans/:**
- Design docs from last 14 days
- 2025-12-09-disaster-recovery-design.md (reference)
- Active implementation plans

---

### Orphan Documents

**Move to plans/ or archive:**

| Document | Current Location | Action |
|----------|-----------------|--------|
| 225-LAMBDA-IMPORT-PLAN.md | docs/ | Move to plans/ |
| FIX_CROSS_ACCOUNT_TERRAFORM_STATE_ACCESS.md | docs/ | Archive |

---

### Stale Documents

**Update or delete:**

| Document | Issue | Action |
|----------|-------|--------|
| API.md | Outdated endpoints | Merge into API_REFERENCE.md, delete |
| DEVELOPMENT.md | References unused Docker | Update for current workflow |
| ROADMAP.md | Many completed items | Clean up, archive completed |

---

## 5. Terraform READMEs Missing

**Modules needing README.md:**

| Module | Priority | Content Needed |
|--------|----------|----------------|
| `analysis-worker/` | High | SQS+Lambda architecture, usage |
| `eval-runbook-worker/` | High | Differences from analysis-worker |
| `scraper-lambda/` | High | Container deployment, warmup |
| `landing-site/` | Medium | S3+CloudFront OAC setup |
| `dns/` | Low | Record structure, staging vs prod |

---

## 6. INFRASTRUCTURE.md Additions

**Topics to add:**

1. **Async Workers Section**
   - Analysis worker (SQS+Lambda)
   - Eval-runbook worker (SQS+Lambda)
   - DLQ configuration
   - Job flow diagram

2. **Scraper Lambda Section**
   - Container-based Lambda
   - ECR lifecycle policy
   - Warmup scheduling

3. **Cross-region Bedrock**
   - Inference profiles (`us.anthropic.*`)
   - Why cross-region is used

---

## 7. Execution Order

### Phase 4a: Quick Wins (1-2 hours)
1. Create `docs/INDEX.md` (navigation hub)
2. Move orphan docs to plans/
3. Archive old plan documents
4. Update session README status

### Phase 4b: CLAUDE.md Reduction (2-3 hours)
1. Extract troubleshooting → OPERATIONS.md (new)
2. Extract staging workflow → DEPLOYMENT.md
3. Extract branching strategy → CI_CD.md
4. Extract Terraform guidelines → INFRASTRUCTURE.md
5. Validate CLAUDE.md < 20KB

### Phase 4c: Documentation Gaps (3-4 hours)
1. Create OPERATIONS.md runbook
2. Expand BEDROCK.md with Napoleon framework
3. Create scraper/README.md
4. Add missing API endpoints to API_REFERENCE.md
5. Delete obsolete API.md

### Phase 4d: Diagrams (2-3 hours)
1. Bedrock retry/backoff sequence (BEDROCK.md)
2. Async job architecture (INFRASTRUCTURE.md)
3. eBay listing import flow (FEATURES.md)
4. Auth flow diagram (FEATURES.md)

### Phase 4e: Terraform READMEs (1-2 hours)
1. analysis-worker/README.md
2. eval-runbook-worker/README.md
3. scraper-lambda/README.md

### Phase 4f: Validation
1. Verify every doc reachable from INDEX.md in 2 clicks
2. Check no orphan documents
3. Confirm CLAUDE.md < 20KB
4. Update session README with completion status

---

## 8. Definition of Done

- [ ] INDEX.md created with all documents linked
- [ ] Every doc reachable within 2 clicks from INDEX.md
- [ ] No orphan documents
- [ ] CLAUDE.md under 20KB
- [ ] OPERATIONS.md created with runbooks
- [ ] API_REFERENCE.md complete with all endpoints
- [ ] High-priority diagrams created (4 minimum)
- [ ] Terraform module READMEs created (3 minimum)
- [ ] Archive directory created with old plans
- [ ] Session documentation complete

---

## 9. Post-Review Actions

### GitHub Issues to Create

| Issue | Priority | Labels |
|-------|----------|--------|
| Add remaining carrier API support (tracking.py:218) | Low | enhancement |
| Document CloudWatch alarms | Medium | documentation |
| Add alerting for async worker failures | Medium | ops |

### Future Improvements (Not in Scope)

- Interactive API documentation (Swagger/OpenAPI)
- Automated documentation generation from code
- Documentation linting/validation in CI
