# Code Feature Audit

**Generated:** 2025-12-21
**Status:** Complete

## Summary

| Area | Files Audited | Features Found | Doc Gaps Identified |
|------|---------------|----------------|---------------------|
| Backend Services | 10 | 35+ | 18 |
| Backend API Endpoints | 8 | 25+ | 12 |
| Infrastructure | 14 modules | 40+ resources | 8 |
| Frontend | Pending | - | - |
| Scripts/Scraper | Pending | - | - |

---

## Backend Services

### `bedrock.py` (~621 lines)

**Purpose:** AWS Bedrock/Claude integration for AI analysis

**Features Found:**

| Feature | Lines | Documented? | Needs Diagram? |
|---------|-------|-------------|----------------|
| Exponential backoff retry | 50-80 | **NO** | YES - sequence diagram |
| Image resizing (PIL/5MB limit) | 120-180 | **NO** | No |
| Prompt caching with TTL | 200-250 | **NO** | No |
| Two-stage extraction (analysis → structured) | 300-400 | **NO** | YES - flow diagram |
| Model selection (sonnet/opus) | 40-50 | Partial in BEDROCK.md | No |
| Cross-region inference profiles | 357 | **NO** | No |

**Retry Logic Details (UNDOCUMENTED):**

```python
delay = base_delay * (2**attempt) + random.uniform(0, 1)  # Jitter
max_retries = 3, base_delay = 5.0 seconds
```

**Documentation Needs:**

- [ ] Sequence diagram for retry/backoff flow
- [ ] Flow diagram for two-stage extraction
- [ ] Update BEDROCK.md with error handling section

---

### `scoring.py` (~639 lines)

**Purpose:** Investment scoring engine for book acquisition decisions

**Features Found:**

| Feature | Lines | Documented? |
|---------|-------|-------------|
| `calculate_investment_grade()` | 80-150 | **NO** |
| `calculate_strategic_fit()` | 160-230 | **NO** |
| `calculate_collection_impact()` | 240-310 | **NO** |
| `is_duplicate_title()` - fuzzy matching | 400-450 | **NO** |
| Author priority scoring | 320-380 | **NO** |

**Score Components (UNDOCUMENTED):**

- Investment Grade: Publisher tier + binder tier + era + condition
- Strategic Fit: Author presence + publisher match + set completion
- Collection Impact: Gap filling + author depth + rarity

**Documentation Needs:**

- [ ] Scoring formula reference (decision tree or table)
- [ ] Tier definitions (TIER_1, TIER_2 publishers/binders)

---

### `tiered_scoring.py` (~427 lines)

**Purpose:** Tiered recommendation system (newer, replaces simple ACQUIRE/PASS)

**Features Found:**

| Feature | Lines | Documented? |
|---------|-------|-------------|
| Quality Score calculation | 38-111 | Design doc only |
| Strategic Fit Score | 121-157 | Design doc only |
| Price Position (EXCELLENT/GOOD/FAIR/POOR) | 170-195 | **NO** |
| Combined Score with weights | 198-212 | Design doc only |
| Recommendation matrix | 226-301 | Design doc only |
| Floor rules (quality/strategic) | 216-218, 258-300 | **NO** |
| Suggested offer calculation | 318-351 | **NO** |

**Documentation Needs:**

- [ ] Move tiered-recommendations-design.md content to main docs
- [ ] Decision matrix table for operations reference
- [ ] Floor rule explanations

---

### `fmv_lookup.py` (~821 lines)

**Purpose:** Fair Market Value lookup from eBay sold listings and AbeBooks

**Features Found:**

| Feature | Lines | Documented? |
|---------|-------|-------------|
| Scraper Lambda invocation | 46-106 | **NO** |
| Playwright-based extraction | 109-170 | **NO** |
| Context-aware query building | 199-256 | **NO** |
| Claude filtering for relevance | 259-352 | **NO** |
| Weighted FMV calculation | 355-414 | **NO** |
| Era-aware filtering | 294-300, 504-512 | **NO** |

**Integration Points (UNDOCUMENTED):**

- Uses `scraper` Lambda for eBay (bot detection avoidance)
- Uses direct HTTP for AbeBooks
- Relevance scoring: HIGH/MEDIUM/LOW

**Documentation Needs:**

- [ ] FMV lookup flow diagram
- [ ] Scraper Lambda integration documentation
- [ ] Confidence level explanations

---

### `eval_generation.py` (~774 lines)

**Purpose:** Evaluation runbook generation with Claude Vision analysis

**Features Found:**

| Feature | Lines | Documented? |
|---------|-------|-------------|
| Claude Vision image analysis | 200-379 | **NO** |
| Condition assessment scoring | 105-139 | **NO** |
| Binding authentication check | 142-172 | **NO** |
| Victorian era scoring | 84-91 | **NO** |
| Unrelated image detection | 269-306 | **NO** |
| Full eval runbook generation | 382-748 | **NO** |

**Scoring Criteria (6 total, 120 max points):**

1. Tier 1 Publisher (20 pts)
2. Victorian Era (30 pts)
3. Complete Set (20 pts)
4. Condition (15 pts)
5. Premium Binding (15 pts)
6. Price vs FMV (20 pts)

**Documentation Needs:**

- [ ] Eval runbook scoring breakdown table
- [ ] Claude Vision analysis prompts documentation
- [ ] Condition grade mapping

---

### `archive.py` (~99 lines)

**Purpose:** Wayback Machine integration for archiving eBay listings

**Features Found:**

| Feature | Lines | Documented? |
|---------|-------|-------------|
| `archive_url()` - save to Wayback | 21-73 | **NO** |
| `check_archive_availability()` | 76-98 | **NO** |

**Documentation Needs:**

- [ ] Add to FEATURES.md or create archive section

---

### `listing.py` (~410 lines)

**Purpose:** eBay listing extraction and processing

**Features Found:**

| Feature | Lines | Documented? |
|---------|-------|-------------|
| eBay URL validation | 23-41 | **NO** |
| Short URL resolution (ebay.us, alphanumeric) | 44-141 | **NO** |
| Fuzzy name matching (Jaccard similarity) | 167-207 | **NO** |
| Bedrock extraction for listings | 336-386 | **NO** |
| HTML content extraction | 251-333 | **NO** |

**Documentation Needs:**

- [ ] eBay URL formats supported
- [ ] Reference matching thresholds

---

### `tracking.py` (~224 lines)

**Purpose:** Shipment tracking utilities

**Features Found:**

| Feature | Lines | Documented? |
|---------|-------|-------------|
| Carrier auto-detection | 40-57 | **NO** |
| Tracking URL generation | 60-77 | **NO** |
| UPS API integration | 144-196 | **NO** |

**Supported Carriers:**

- UPS (full API integration)
- USPS, FedEx, DHL, Royal Mail, Parcelforce (URL generation only)

**TODO Found (Line 218):**
> `# TODO: Add support for USPS, FedEx, etc.`

**Documentation Needs:**

- [ ] Tracking feature documentation in FEATURES.md
- [ ] GitHub issue for additional carrier support

---

### `sqs.py` (~119 lines)

**Purpose:** SQS message sending for async jobs

**Features Found:**

| Feature | Lines | Documented? |
|---------|-------|-------------|
| Analysis job queue | 63-90 | **NO** |
| Eval runbook job queue | 93-118 | **NO** |

**Documentation Needs:**

- [ ] Async job architecture diagram

---

## Backend API Endpoints

### `health.py` (~746 lines)

**Purpose:** Health checks, migrations, cleanup

**Endpoints Found:**

| Endpoint | Method | Documented in API_REFERENCE? |
|----------|--------|------------------------------|
| `/health/live` | GET | **NO** |
| `/health/ready` | GET | **NO** |
| `/health/deep` | GET | **NO** |
| `/health/info` | GET | **NO** |
| `/health/version` | GET | **NO** |
| `/health/migrate` | POST | **NO** |
| `/health/cleanup-orphans` | POST | **NO** |

**Documentation Needs:**

- [ ] Add all health endpoints to API_REFERENCE.md
- [ ] Create operations runbook for migrations

---

### `listings.py` (~404 lines)

**Purpose:** eBay listing extraction API

**Endpoints Found:**

| Endpoint | Method | Documented in API_REFERENCE? |
|----------|--------|------------------------------|
| `/listings/extract` | POST | **NO** |
| `/listings/extract-async` | POST | **NO** |
| `/listings/extract/{item_id}/status` | GET | **NO** |

**Documentation Needs:**

- [ ] Add listings endpoints to API_REFERENCE.md with examples
- [ ] Document async extraction flow

---

### `eval_runbook.py` (~240 lines)

**Purpose:** Evaluation runbook management

**Endpoints Found:**

| Endpoint | Method | Documented in API_REFERENCE? |
|----------|--------|------------------------------|
| `/eval-runbooks` | GET | **NO** |
| `/eval-runbooks/price` | PATCH | **NO** |
| `/eval-runbooks/history` | GET | **NO** |
| `/eval-runbooks/refresh` | POST | **NO** |

**Documentation Needs:**

- [ ] Add eval runbook endpoints to API_REFERENCE.md

---

### `books.py` (~300+ lines examined)

**Purpose:** Book CRUD operations

**Features Found:**

| Feature | Documented? |
|---------|-------------|
| Full-text search (q parameter) | Partial |
| Extensive filtering (20+ filters) | **NO** |
| Score calculation on update | **NO** |
| Image copying from listings | **NO** |
| Thumbnail generation | **NO** |

**Documentation Needs:**

- [ ] Complete filter parameter documentation
- [ ] Scoring recalculation triggers

---

## Infrastructure (Terraform)

### Overview

**Location:** `infra/terraform/`
**Total Modules:** 14
**Modules with READMEs:** 9
**Modules missing READMEs:** 5

### Module Inventory

| Module | Purpose | Has README? | Documented in INFRASTRUCTURE.md? |
|--------|---------|-------------|----------------------------------|
| `api-gateway/` | HTTP API + custom domain | YES | YES |
| `cloudfront/` | CDN distributions | YES | YES |
| `cognito/` | User pools + clients | YES | YES |
| `db-sync-lambda/` | Prod→Staging data sync | YES | Partial |
| `dns/` | Route 53 records | **NO** | Partial |
| `github-oidc/` | GitHub Actions auth | YES | YES |
| `lambda/` | API function + IAM | YES | YES |
| `landing-site/` | Marketing site (S3+CloudFront) | **NO** | Partial |
| `rds/` | Aurora Serverless v2 | YES | YES |
| `s3/` | Buckets + policies | YES | YES |
| `secrets/` | DB credentials | NO (simple) | YES |
| `vpc-networking/` | VPC endpoints, NAT gateway | YES | Partial |
| `analysis-worker/` | Async Bedrock analysis (SQS+Lambda) | **NO** | **NO** |
| `eval-runbook-worker/` | Async eval runbook (SQS+Lambda) | **NO** | **NO** |
| `scraper-lambda/` | Playwright-based eBay scraping | **NO** | **NO** |

---

### Modules Missing README Documentation

#### `analysis-worker/` (~265 lines)

**Purpose:** Async analysis generation bypassing API Gateway's 29s timeout

**Resources Created:**

- SQS queue + DLQ with redrive policy
- Lambda function (600s timeout)
- IAM role with Bedrock, Secrets Manager, S3 access
- Event source mapping (batch_size=1)

**Documentation Needs:**

- [ ] README.md with usage example
- [ ] Document worker handler entry point

---

#### `eval-runbook-worker/` (~284 lines)

**Purpose:** Async eval runbook generation with FMV lookup

**Resources Created:**

- SQS queue + DLQ with redrive policy
- Lambda function (600s timeout)
- IAM role with Bedrock, Secrets Manager, S3, Lambda invoke access
- Event source mapping (batch_size=1)

**Documentation Needs:**

- [ ] README.md with usage example
- [ ] Document differences from analysis-worker (Lambda invoke permission for scraper)

---

#### `scraper-lambda/` (~268 lines)

**Purpose:** Container-based Playwright scraping for eBay

**Resources Created:**

- ECR repository (immutable tags, scan on push)
- Lambda function (container image, 120s timeout)
- Optional provisioned concurrency
- EventBridge warmup rule (keeps container warm)

**Documentation Needs:**

- [ ] README.md explaining container deployment process
- [ ] ECR lifecycle policy documentation
- [ ] Warmup scheduling explanation

---

#### `landing-site/` (~137 lines)

**Purpose:** Marketing site with S3 + CloudFront using OAC

**Resources Created:**

- S3 bucket (versioned, encrypted)
- CloudFront OAC (modern approach, not OAI)
- CloudFront distribution with SPA error handling
- S3 bucket policy for CloudFront

**Documentation Needs:**

- [ ] README.md with deployment instructions

---

#### `dns/` (~180 lines)

**Purpose:** Route53 hosted zone and DNS records

**Resources Created:**

- Route53 hosted zone
- A/AAAA records for: bluemoxon.com, www, app, staging.app
- Alias records for API Gateway (api, staging.api)

**Documentation Needs:**

- [ ] README.md explaining record structure
- [ ] Document staging vs. prod DNS differences

---

### INFRASTRUCTURE.md Gaps

| Topic | Current State | Gap |
|-------|--------------|-----|
| Async workers (SQS+Lambda) | **Not documented** | Analysis and eval-runbook workers not mentioned |
| Scraper Lambda | **Not documented** | Container-based Playwright Lambda not mentioned |
| Worker job flow | **Not documented** | No diagram showing SQS→Lambda→DLQ flow |
| VPC endpoints | Partial | Missing explanation of why some endpoints disabled |
| Cross-region inference | **Not documented** | Bedrock inference profiles not explained |
| ECR lifecycle | **Not documented** | Image retention policy not documented |

---

### Infrastructure Diagrams Needed

| Diagram Type | Topic | Purpose |
|--------------|-------|---------|
| Sequence | SQS worker job flow | Show API → SQS → Worker → DLQ path |
| Component | Async job architecture | Show analysis/eval-runbook workers + queues |
| Flow | Scraper Lambda container build | CI/CD deployment of container images |

---

### Infrastructure Documentation Notes

**Existing INFRASTRUCTURE.md is comprehensive for:**

- VPC networking (subnets, route tables, security groups)
- Database (Aurora Serverless v2)
- Authentication (Cognito)
- API Gateway and Lambda
- CloudFront and S3
- Monitoring (CloudWatch dashboard, alarms)

**Needs additions:**

1. **Async Worker Architecture** - The analysis-worker and eval-runbook-worker modules create SQS-triggered Lambdas that bypass API Gateway's 29-second timeout. This architectural pattern is not documented.

2. **Scraper Lambda** - Container-based Lambda for Playwright browser automation is not documented. Uses ECR repository with lifecycle policy.

3. **Cross-region Bedrock** - Workers use cross-region inference profiles (`us.anthropic.*`) for model availability.

---

## Diagrams Needed

### High Priority

| Diagram Type | Topic | Purpose |
|--------------|-------|---------|
| Sequence | Bedrock retry/backoff | Operations troubleshooting |
| Flow | eBay listing import pipeline | Developer understanding |
| Flow | Eval runbook generation | Feature understanding |
| Sequence | Async job processing (SQS) | Architecture documentation |

### Medium Priority

| Diagram Type | Topic | Purpose |
|--------------|-------|---------|
| Component | Scoring engine data flow | Developer onboarding |
| Flow | FMV lookup process | Feature understanding |
| Architecture | Lambda + VPC + RDS | Infrastructure overview |
| Sequence | SQS worker job flow | Show API → SQS → Worker → DLQ |
| Component | Async job architecture | Analysis + eval-runbook workers |
| Flow | Scraper Lambda container build | CI/CD deployment |

---

## GitHub Issues to Create

### Unfinished Implementations

| Finding | Location | Priority |
|---------|----------|----------|
| Carrier API support incomplete | `tracking.py:218` | Low |

### Missing Features (Referenced but not implemented)

*None identified during backend audit*

### Infrastructure Gaps

| Finding | Location | Impact |
|---------|----------|--------|
| No alerts documented | health.py checks | Ops |
| Async workers not documented | INFRASTRUCTURE.md | Dev/Ops |
| Scraper Lambda not documented | INFRASTRUCTURE.md | Dev/Ops |
| 5 Terraform modules missing READMEs | infra/terraform/modules/ | Dev |
| Cross-region Bedrock not explained | INFRASTRUCTURE.md | Dev |

### Code to Deprecate/Remove

*None identified during backend audit*

---

## Frontend (Vue 3 + TypeScript)

### Overview

**Framework:** Vue 3 with Composition API + TypeScript
**State Management:** Pinia stores
**UI Framework:** Tailwind CSS with Victorian design system
**Charts:** Chart.js
**Markdown:** marked + DOMPurify

### Router (`router/index.ts` ~145 lines)

**Routes Found:** 11 total

| Route | Purpose | Auth | Documented? |
|-------|---------|------|-------------|
| `/` | Home/redirect | No | **NO** |
| `/login` | Login page | No | **NO** |
| `/mfa-setup` | MFA configuration | Auth | **NO** |
| `/dashboard` | Main dashboard | Auth | **NO** |
| `/books` | Book collection list | Auth | **NO** |
| `/books/:id` | Book detail view | Auth | **NO** |
| `/acquisitions` | Kanban workflow | Auth | **NO** |
| `/insurance-report` | Insurance reports | Auth | **NO** |
| `/admin/users` | User management | Admin | **NO** |
| `/settings` | User settings | Auth | **NO** |
| `/callback` | OAuth callback | No | **NO** |

**Auth Features (UNDOCUMENTED):**

- `requiresAuth` meta guard
- `requiresAdmin` meta guard
- MFA setup redirect flow
- Auth initialization on first navigation

**Documentation Needs:**

- [ ] Route documentation in FEATURES.md
- [ ] Auth flow diagram (login → MFA → dashboard)

---

### Pinia Stores

**Pattern (UNDOCUMENTED):**

```typescript
// Async job tracking with reactive Map
activeAnalysisJobs: new Map<number, ReturnType<typeof setInterval>>()
activeEvalRunbookJobs: new Map<number, ReturnType<typeof setInterval>>()
```

**Stores Found:**

| Store | Purpose | Documented? |
|-------|---------|-------------|
| `booksStore` | Book CRUD + job polling | **NO** |
| `authStore` | Cognito auth state | **NO** |
| `usersStore` | User management | **NO** |

**Documentation Needs:**

- [ ] State management patterns documentation
- [ ] Job polling architecture diagram

---

### Key Components

#### `EvalRunbookModal.vue` (~838 lines)

**Purpose:** Evaluation runbook display with tiered recommendations

**Features Found:**

| Feature | Documented? |
|---------|-------------|
| Tiered recommendation badges (STRONG_BUY, BUY, CONDITIONAL, PASS) | Design doc only |
| Napoleon override indicator | **NO** |
| Price editing with score impact preview | **NO** |
| FMV comparables display (eBay, AbeBooks) | **NO** |
| Suggested offer display | **NO** |

**Tier Badge Config (UNDOCUMENTED):**

```typescript
const configs: Record<string, { bg: string; text: string; icon: string }> = {
  STRONG_BUY: { bg: "bg-green-500", text: "text-white", icon: "✓✓" },
  BUY: { bg: "bg-green-100", text: "text-green-800", icon: "✓" },
  CONDITIONAL: { bg: "bg-amber-100", text: "text-amber-800", icon: "⚠" },
  PASS: { bg: "bg-gray-100", text: "text-gray-800", icon: "✗" },
};
```

---

#### `AnalysisViewer.vue` (~886 lines)

**Purpose:** AI analysis display with markdown rendering

**Features Found:**

| Feature | Documented? |
|---------|-------------|
| Markdown rendering (marked + DOMPurify) | **NO** |
| Napoleon v2 STRUCTURED-DATA stripping | **NO** |
| Model selection (Sonnet/Opus) | **NO** |
| Print functionality | **NO** |
| Split-pane editor | **NO** |

**Napoleon v2 Stripping (UNDOCUMENTED):**

```typescript
function stripStructuredData(markdown: string): string {
  result = result.replace(/---STRUCTURED-DATA---[\s\S]*?---END-STRUCTURED-DATA---\s*/gi, "");
  return result;
}
```

**Documentation Needs:**

- [ ] Napoleon v2 format documentation
- [ ] Print stylesheet documentation

---

#### `AcquireModal.vue` (~370 lines)

**Purpose:** Book acquisition with currency conversion

**Features Found:**

| Feature | Documented? |
|---------|-------------|
| Currency selection (USD/GBP/EUR) | **NO** |
| Exchange rate lookup | **NO** |
| Price conversion | **NO** |
| Paste order integration | **NO** |

**Currency Conversion (UNDOCUMENTED):**

```typescript
const priceInUsd = computed(() => {
  switch (selectedCurrency.value) {
    case "GBP": return form.value.purchase_price * exchangeRates.value.gbp_to_usd_rate;
    case "EUR": return form.value.purchase_price * exchangeRates.value.eur_to_usd_rate;
    default: return form.value.purchase_price;
  }
});
```

---

#### `StatisticsDashboard.vue` (~448 lines)

**Purpose:** Chart.js analytics with Victorian design

**Features Found:**

| Feature | Documented? |
|---------|-------------|
| Acquisitions growth chart (Line) | **NO** |
| Bindings distribution chart (Doughnut) | **NO** |
| Era distribution chart (Bar) | **NO** |
| Publishers chart (Bar) | **NO** |
| Authors chart (Bar) | **NO** |
| Victorian color scheme | **NO** |

**Victorian Chart Colors (UNDOCUMENTED):**

```typescript
const chartColors = {
  primary: "rgb(26, 58, 47)",    // victorian-hunter-800
  gold: "rgb(201, 162, 39)",     // victorian-gold
  burgundy: "rgb(114, 47, 55)",  // victorian-burgundy
};
```

**Documentation Needs:**

- [ ] Victorian design system documentation
- [ ] Chart.js integration patterns

---

### Key Views

#### `InsuranceReportView.vue` (~554 lines)

**Purpose:** Insurance and collection reports

**Features Found:**

| Feature | Documented? |
|---------|-------------|
| 4 report types (insurance, primary, extended, all) | **NO** |
| CSV export | **NO** |
| Print functionality with styles | **NO** |
| Collection statistics calculation | **NO** |
| Dynamic filtering | **NO** |

**Report Types (UNDOCUMENTED):**

- Insurance: For insurance purposes (replacement values)
- Primary: Core collection items
- Extended: Full collection with variants
- All: Complete inventory

---

#### `AcquisitionsView.vue` (~1148 lines)

**Purpose:** Kanban workflow for book acquisition

**Features Found:**

| Feature | Documented? |
|---------|-------------|
| Kanban columns (Evaluating → In Transit → Received) | Design doc only |
| Async job status syncing | **NO** |
| Job polling across sessions | **NO** |
| Analysis job management | **NO** |
| Eval runbook job management | **NO** |
| Column counts and metrics | **NO** |

**Job Syncing Pattern (UNDOCUMENTED):**

```typescript
function syncBackendJobPolling() {
  for (const book of evaluating.value) {
    if ((book.eval_runbook_job_status === "running" || book.eval_runbook_job_status === "pending") &&
        !activeEvalRunbookJobs.value.has(book.id)) {
      booksStore.startEvalRunbookJobPoller(book.id);
    }
  }
}
```

---

### Frontend Documentation Gaps

| Topic | Current State | Gap |
|-------|--------------|-----|
| Victorian design system | Not documented | Color palette, typography, component styles |
| Async job tracking | Not documented | Polling pattern, Map reactivity, session sync |
| Currency conversion | Not documented | Exchange rate sources, conversion logic |
| Print functionality | Not documented | Print stylesheets, page breaks |
| Kanban workflow | Design doc only | Full workflow with job states |
| Chart.js integration | Not documented | Chart types, data sources, colors |
| Markdown rendering | Not documented | marked config, DOMPurify sanitization |
| Napoleon v2 format | Not documented | STRUCTURED-DATA block format |

---

### Frontend Diagrams Needed

| Diagram Type | Topic | Purpose |
|--------------|-------|---------|-
| Flow | Auth flow (login → MFA → dashboard) | User documentation |
| Flow | Acquisition workflow (Kanban states) | Feature understanding |
| Sequence | Async job polling | Developer understanding |
| Component | Victorian design system | Design reference |

---

## Scripts, Scraper & Prompts

### Scripts (`scripts/`)

**Total: 15 scripts**

#### Development Workflow Scripts

| Script | Lines | Purpose | Documented? |
|--------|-------|---------|-------------|
| `validate-and-push.sh` | ~67 | Local validation → PR → CI → Merge | Partial in CLAUDE.md |
| `setup-dev.sh` | ~43 | Install pre-commit hooks, deps | **NO** |
| `validate.sh` | ? | Run linters locally | **NO** |
| `pr-workflow.sh` | ? | PR automation | **NO** |
| `dev.sh` | ? | Local dev startup | **NO** |

**`validate-and-push.sh` Features (UNDOCUMENTED):**

- Backend lint (ruff check + format)
- Frontend lint + type-check
- Branch protection (blocks push to main)
- Auto PR creation with test plan
- CI watch and auto-merge

---

#### Data Management Scripts

| Script | Lines | Purpose | Documented? |
|--------|-------|---------|-------------|
| `sync-prod-to-staging.sh` | ~339 | S3 + DB sync from prod → staging | **NO** |
| `import_assets.py` | ~420 | Import images/analyses from book-collection | **NO** |
| `generate_thumbnails.py` | ~99 | Generate thumbnails for existing images | **NO** |
| `seed_from_csv.py` | ? | Seed database from CSV | **NO** |
| `update_titles.py` | ? | Batch update book titles | **NO** |

**`sync-prod-to-staging.sh` Features (UNDOCUMENTED):**

- S3 cross-account sync (download/upload pattern)
- Database dump and restore
- Secrets Manager credential lookup
- Dry-run mode
- Confirmation prompts

**`import_assets.py` Features (UNDOCUMENTED):**

- Word-based fuzzy matching for book titles
- EXIF transpose for image orientation
- Thumbnail generation on import
- Analysis markdown extraction

---

#### Infrastructure Scripts

| Script | Lines | Purpose | Documented? |
|--------|-------|---------|-------------|
| `bootstrap-staging-terraform.sh` | ? | Initial Terraform setup | **NO** |
| `setup-github-oidc.sh` | ? | GitHub OIDC trust setup | **NO** |
| `deploy-landing.sh` | ? | Marketing site deploy | **NO** |
| `deploy-db-sync-lambda.sh` | ? | DB sync Lambda deploy | **NO** |
| `monitor-capacity.sh` | ? | RDS capacity monitoring | **NO** |

---

### Scraper Lambda (`scraper/`)

**Purpose:** Container-based Playwright Lambda for eBay scraping

#### `handler.py` (~434 lines)

**Features Found:**

| Feature | Lines | Documented? |
|---------|-------|-------------|
| Playwright headless Chrome | 228-246 | **NO** |
| eBay item ID extraction | 37-45 | **NO** |
| Banner detection (aspect ratio) | 48-86 | **NO** |
| Image upload to S3 | 171-184 | **NO** |
| Rate limiting detection | 296-315 | **NO** |
| Warmup handler (container warm) | 202-205 | **NO** |
| Search results extraction (FMV) | 89-168, 318-336 | **NO** |
| Image filtering (min size, banners) | 379-387 | **NO** |

**Key Patterns (UNDOCUMENTED):**

**Banner Detection:**

```python
BANNER_ASPECT_RATIO_THRESHOLD = 2.0  # width/height > 2.0 = likely banner
BANNER_POSITION_WINDOW = 3  # Check last N images in carousel
```

**Lambda Launch Args (for container):**

```python
args=[
    "--single-process",
    "--no-zygote",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
]
```

**Rate Limiting Patterns:**

- "access denied"
- "blocked by ebay"
- "complete the captcha"
- Returns 429 status

**Container Components:**

| File | Purpose | Documented? |
|------|---------|-------------|
| `Dockerfile` | Playwright container build | **NO** |
| `requirements.txt` | Python dependencies | N/A |
| `test_handler.py` | Handler tests | N/A |

---

### Prompts (`prompts/`)

#### Napoleon Framework v2 (`prompts/napoleon-framework/v2.md` ~368 lines)

**Purpose:** AI analysis prompt for book valuations

**Features Found:**

| Feature | Documented? |
|---------|-------------|
| STRUCTURED-DATA block format | **NO** (frontend strips it) |
| Condition grade standards (ABAA-based) | **NO** |
| Binder identification tiers (Tier 1/Tier 2) | **NO** |
| 13-section analysis structure | **NO** |
| Metadata block (first edition, provenance) | **NO** |
| Binding elaborateness classification | **NO** |
| Market analysis requirements | **NO** |

**STRUCTURED-DATA Format (UNDOCUMENTED):**

```text
---STRUCTURED-DATA---
CONDITION_GRADE: [Fine|VG+|VG|VG-|Good+|Good|Fair|Poor]
BINDER_IDENTIFIED: [Binder Name|UNKNOWN]
BINDER_CONFIDENCE: [HIGH|MEDIUM|LOW|NONE]
BINDING_TYPE: [Full Morocco|Half Morocco|...]
VALUATION_LOW: [number]
VALUATION_MID: [number]
VALUATION_HIGH: [number]
ERA_PERIOD: [Victorian|Romantic|Georgian|Edwardian|Modern]
PUBLICATION_YEAR: [year or UNKNOWN]
---END-STRUCTURED-DATA---
```

**Binder Tiers (UNDOCUMENTED):**

| Tier | Binders | Notes |
|------|---------|-------|
| Tier 1 (Premium) | Sangorski & Sutcliffe, Rivière & Son, Zaehnsdorf, Cobden-Sanderson, Bedford | Signed, premium pricing |
| Tier 2 (Quality) | Morrell, Root & Son, Bayntun, Tout, Stikeman | Signed, quality work |

**Metadata Block (UNDOCUMENTED):**

```html
<!-- METADATA_START -->
{
  "is_first_edition": true | false | null,
  "has_provenance": true | false,
  "provenance_tier": "Tier 1" | "Tier 2" | "Tier 3" | null
}
<!-- METADATA_END -->
```

---

### Scripts/Scraper/Prompts Documentation Gaps

| Topic | Current State | Gap |
|-------|--------------|-----|
| Development workflow scripts | Partial in CLAUDE.md | Full usage documentation |
| Data sync procedures | Not documented | Runbook with prerequisites |
| Scraper Lambda architecture | Not documented | Container build/deploy process |
| Rate limiting handling | Not documented | Error handling and retry strategy |
| Napoleon framework | Not documented | Prompt structure and field extraction |
| STRUCTURED-DATA parsing | Not documented | Frontend/backend extraction logic |
| Binder identification | Not documented | Tier definitions and confidence levels |
| Image import pipeline | Not documented | Asset migration workflow |

---

### Scripts Documentation Needed

| Script | Documentation Type |
|--------|-------------------|
| `validate-and-push.sh` | Add to DEVELOPMENT.md |
| `sync-prod-to-staging.sh` | Add to DATABASE_SYNC.md or new OPERATIONS.md |
| `import_assets.py` | Add to data migration runbook |
| Scraper handler | Add to INFRASTRUCTURE.md + README in scraper/ |
| Napoleon v2 | Add to PROMPTS.md (new) or BEDROCK.md |

---

## Summary Statistics

| Area | Files Audited | Features Found | Doc Gaps |
|------|---------------|----------------|----------|
| Backend Services | 10 | 35+ | 18 |
| Backend API Endpoints | 8 | 25+ | 12 |
| Infrastructure | 14 modules | 40+ resources | 8 |
| Frontend | 12 components | 30+ | 15 |
| Scripts/Scraper/Prompts | 18 files | 25+ | 12 |
| **Total** | **62** | **155+** | **65** |

---

## Next Steps

1. ~~**Infrastructure Audit** - Terraform modules, AWS resources~~ ✓
2. ~~**Frontend Audit** - Vue components, API integration~~ ✓
3. ~~**Scripts/Scraper/Prompts Audit** - Utility scripts, scraper Lambda, AI prompts~~ ✓
4. **Gap Analysis** - Cross-reference inventory with audit findings
