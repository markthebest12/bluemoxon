# BlueMoxon Feature Roadmap

This document tracks planned features, improvements, and technical debt for the BlueMoxon Victorian Book Collection application.

**Target Budget:** $40-50/month (internal family use only)

---

## Table of Contents

1. [Application Features](#application-features)
   - [Major Feature Initiatives](#major-feature-initiatives) — Social Circles, AI Connections, Literary London
   - [Other Feature Ideas](#other-feature-ideas)
2. [Infrastructure & Resiliency](#infrastructure--resiliency)
3. [Frontend Performance](#frontend-performance)
4. [CI/CD Improvements](#cicd-improvements)
5. [Priority Matrix](#priority-matrix)

---

## Application Features

### In-Code TODOs

| Feature | Location | Priority | Effort | Status |
|---------|----------|----------|--------|--------|
| ~~**Thumbnail Generation**~~ | `backend/app/api/v1/images.py` | ~~Medium~~ | ~~Medium~~ | ✅ DONE |

*Thumbnail generation: Pillow-based 300x300 JPEG thumbnails on upload and import.*

### Testing Gaps

| Feature | Description | Priority | Effort | Status |
|---------|-------------|----------|--------|--------|
| ~~**Playwright E2E Tests**~~ | ~~End-to-end browser testing~~ | ~~Low~~ | ~~High~~ | ✅ Configured |
| ~~**Vitest Frontend Unit Tests**~~ | ~~27 tests passing (books store + insurance report)~~ | ~~Medium~~ | ~~Medium~~ | ✅ DONE |
| ~~**Prettier Configuration**~~ | ~~Code formatting~~ | ~~Low~~ | ~~Low~~ | ✅ DONE |

### Missing UI Features

| Feature | Description | Priority | Effort | Status |
|---------|-------------|----------|--------|--------|
| ~~**Role-Based Authorization**~~ | ~~Admin/editor/viewer roles enforced via `require_admin`, `require_editor`, `require_viewer` dependencies~~ | ~~Low~~ | ~~Medium~~ | ✅ DONE |
| ~~**Book Status Management**~~ | ~~Color-coded dropdown selector on book detail page (ON_HAND, IN_TRANSIT, SOLD, REMOVED)~~ | ~~Medium~~ | ~~Low~~ | ✅ DONE |
| ~~**Provenance Tracking**~~ | ~~View/edit modes for ownership history, inscriptions, bookplates~~ | ~~Low~~ | ~~Low~~ | ✅ DONE |
| ~~**Analysis Management UI**~~ | ~~Split-pane markdown editor with live preview, delete functionality~~ | ~~Medium~~ | ~~Medium~~ | ✅ DONE |
| ~~**Image Gallery Lightbox**~~ | ~~Full-screen image viewer on book detail~~ | ~~Medium~~ | ~~Low~~ | ✅ DONE |
| ~~**Image Drag-and-Drop Reordering**~~ | ~~Drag-and-drop interface for reordering images with display_order persistence~~ | ~~Low~~ | ~~Medium~~ | ✅ DONE |
| ~~**Advanced Filtering**~~ | ~~Filter panel: bindery, publisher, tier, binding type, condition, status, year/value range~~ | ~~Medium~~ | ~~Medium~~ | ✅ DONE |
| ~~**Filter State Persistence**~~ | ~~Filter state preserved on back navigation and "Back to Collection" link~~ | ~~Low~~ | ~~Low~~ | ✅ DONE |

### Major Feature Initiatives

#### Victorian Social Circles — Interactive Network Visualization

The flagship feature of BMX 3.0. An interactive Cytoscape.js network graph showing who knew whom, who published whom, who influenced whom across the collection.

**Vision:** "Your collection isn't just books — it's a map of Victorian intellectual London. Everyone knew everyone. Same publishers, same binderies, same social circles."

**Design:** [`docs/plans/2026-01-26-victorian-social-circles-design.md`](plans/2026-01-26-victorian-social-circles-design.md)

| Phase | Description | Issues | Status |
|-------|-------------|--------|--------|
| **Phase 1: MVP** | Foundation, network graph, tooltips, filters, timeline, detail panel, states, integration | #1316 (epic), #1317-#1347 | ✅ Complete |
| **Phase 2: Enhanced** | Search, find similar, statistics, degrees of separation, layout modes, polish | #1324-#1344 | In Progress |
| **Phase 3: Visual** | Filter badges, mini-map, timeline markers | #1345-#1347 | Planned |

#### AI-Discovered Personal Connections

The social circles system only discovers connections through shared book data (publisher, binder). This misses the most compelling relationships — marriages, friendships, mentorships, and scandals.

**The Browning Problem:** Elizabeth Barrett Browning and Robert Browning have 6 books in the collection but share zero publishers. The most famous literary couple in Victorian England is invisible.

**Solution:** AI-discovered connections at profile generation time. 5 connection types: family, friendship, influence, collaboration, scandal. Zero new infrastructure — uses existing SQS pipeline and entity_profiles table. Cost: ~$0.40 for full 264-entity batch.

**Edge styling:**

- **Green** = publisher relationships
- **Blue** = personal connections (AI-discovered)
- **Purple** = binder relationships
- **Rose** = scandal (the soap opera layer)

**Design:** [`docs/plans/2026-02-04-ai-discovered-connections-design.md`](plans/2026-02-04-ai-discovered-connections-design.md)

| Track | Description | Issue | Status |
|-------|-------------|-------|--------|
| Foundation | Migration + model + schema + frontend types | #1804 | ✅ Complete |
| AI Discovery | `generate_ai_connections()` + validation | #1805 | ✅ Complete |
| Pipeline | Wire into `generate_and_cache_profile()` | #1806 | ✅ Complete |
| Graph Builder | Merge AI edges into social circles graph | #1807 | ✅ Complete |
| Edge Styling | Type-specific colors + click-to-highlight | #1808 | ✅ Complete |
| Badges | Sub_type badges + confidence styling | #1809 | ✅ Complete |
| E2E Tests | Profile + social circles AI connection tests | #1810 | Planned |

**Epic:** #1803

#### "Literary London 1850" — The Walking Tour

An interactive period map of London with actual publisher addresses plotted, showing where the books in the collection were born.

**Concept:** In 1850, you could walk from Chapman & Hall to Smith, Elder in 15 minutes, possibly running into Dickens or Thackeray on the street. This feature makes the geography of Victorian publishing tangible.

**Known addresses:**

| Entity | Address | Notes |
|--------|---------|-------|
| John Murray | 50 Albemarle Street | Still there! |
| Smith, Elder & Co. | 65 Cornhill | Corner of Bishopsgate |
| Chapman & Hall | 186 Strand | |
| Edward Moxon | 44 Dover Street | |
| Macmillan | Cambridge → 16 Bedford Street, Covent Garden | Moved to London 1858 |
| Rivière (binder) | Bath Street | |
| Zaehnsdorf (binder) | Goswell Road | |

**Map layers:**

1. **Publisher locations** — pins with hover showing your books from each publisher
2. **Bindery locations** — Rivière, Zaehnsdorf, and others
3. **Printing houses** — where the physical books were made
4. **Bookseller shops** — Mudie's Lending Library, Hatchard's, etc.

**Interactive features:**

- **Street view** — Click an address and see what it looks like today (many buildings still stand)
- **Timeline slider** — See how the publishing district evolved 1800-1900
- **"Your collection's center of gravity"** — Where most of your books came from geographically
- **Walking routes** — Distances between publishers (they were literally neighbors)

**Tech:** Mapbox or Leaflet with historical map overlay (1850s London)

| Aspect | Details |
|--------|---------|
| Priority | Low (vision feature) |
| Effort | High |
| Dependencies | Social circles data for entity→publisher mapping |
| Data work | Research and verify historical addresses |
| Status | Vision — not yet planned |

---

### Other Feature Ideas

| Feature | Description | Priority | Effort | Status |
|---------|-------------|----------|--------|--------|
| ~~**Collection Statistics Dashboard**~~ | ~~Value growth chart, premium bindings distribution, era breakdown, top publishers~~ | ~~Medium~~ | ~~Medium~~ | ✅ DONE |
| ~~**Insurance/Export Reports**~~ | ~~Insurance valuation report with CSV export, report type selector (Primary/Extended/Full)~~ | ~~Low~~ | ~~High~~ | ✅ DONE |
| **Add Images to Insurance Report** | Include book thumbnails in printable report | Low | Low | |
| **Audit Logging** | Track changes to book records (who changed what and when) | Low | Medium | |
| **Set Completion Detection** | Detect when book completes a set in eval generation (#517) | Medium | Medium | Planned |
| **Carrier API Support** | USPS, FedEx, DHL tracking integration (#516) | Low | High | Planned |
| **Tiered Recommendations** | Offer prices with reasoning in valuations | Medium | Medium | Planned |

### Recently Completed / In Progress (January–February 2026)

| Feature | Description | Status |
|---------|-------------|--------|
| **Victorian Social Circles Phase 1** | Interactive Cytoscape.js network graph — nodes, edges, filters, timeline, tooltips, detail panel | ✅ #1316 |
| **AI-Discovered Connections** | Personal connections (family, friendship, influence, collaboration, scandal) via AI discovery | ✅ #1803 |
| **Entity Profiles & AI Bios** | AI-generated entity profiles with bios, stories, and connection narratives | ✅ Complete |
| **Model Configuration UI** | Per-flow AI model selectors on admin config page (#1571, #1570, #1714) | ✅ #1774, #1775 |
| **Toast Notification System** | User-friendly error/success notifications with hover-to-pause, duplicate suppression | ✅ #855 |
| **Shared Constants Extraction** | Centralized book status and dropdown constants in `frontend/src/constants/` | ✅ #854 |
| **Strict ESLint Rules** | Enabled `@typescript-eslint/no-explicit-any` and `@typescript-eslint/explicit-function-return-type` | ✅ #870 |

### Previously Completed (December 2025)

| Feature | Description | Status |
|---------|-------------|--------|
| **Napoleon Framework v3** | Consolidated prompt directories, renamed v2→v3, added TDD verification test | ✅ #522 |
| **Print Capability** | Print-friendly views for book detail and analysis pages | ✅ #511 |
| **Report Theming** | Consistent theming across insurance report pages | ✅ #510 |
| **CI/CD Smoke Tests** | Comprehensive smoke tests including image CDN validation | ✅ #507 |
| **Provenance Re-analysis** | Batch re-analysis with provenance detection prompt improvements | ✅ #506 |
| **Napoleon Prompt Enrichment** | Enhanced prompts for better valuations and provenance detection | ✅ #502 |
| **Analysis Status Refresh** | Fixed eval runbook and Napoleon analysis requiring browser refresh | ✅ #499 |
| **Ask Price Storage** | Fixed eval books not storing ask price from eBay import | ✅ #498 |
| **URL Shortener Fix** | Fixed broken URLs from eBay shortener links | ✅ #497 |
| **AI Image Filtering** | Filter non-related images from eBay listing imports | ✅ #487 |
| **Acquire Modal Fix** | Fixed clipped modal in desktop browser | ✅ #481 |
| **Provenance & First Edition** | Searchable provenance and first edition fields | ✅ #466 |
| **Analysis Visual Cleanup** | Improved analysis and eval runbook UI | ✅ #461 |
| **Regenerate Analysis UX** | Expanded features for regenerate analysis button | ✅ #459 |
| **Acquisitions UI** | Moved Import/Add buttons, listing links for all statuses | ✅ #457, #456 |
| **Tracking Refresh** | On-demand tracking info refresh button | ✅ #454 |
| **Two-Stage Extraction** | Separated analysis generation from structured data extraction | ✅ #468 |
| **Multi-Currency Support** | Manual entry widget supports GBP/EUR/USD | ✅ #446 |
| **Staging Environment** | Full dual-environment setup with isolated resources | ✅ #429 |
| **CloudFront Path Routing** | /book-images/* routed to images bucket | ✅ #430 |

### Previously Completed (November-Early December 2025)

| Feature | Description | Status |
|---------|-------------|--------|
| **Duplicate Image Detection** | SHA256 content hash prevents uploading identical images | ✅ DONE |
| **Per-User MFA Control** | Admin toggle to exempt specific users from MFA | ✅ DONE |
| **Dashboard Week-over-Week Trends** | Value change indicators comparing to previous week | ✅ DONE |
| **Mobile Responsive UI** | Tailwind breakpoints, touch support, mobile layouts | ✅ DONE |
| **Deep Health Check Endpoints** | `/health/live`, `/ready`, `/deep`, `/info` | ✅ DONE |
| **CloudWatch Monitoring** | 10-panel dashboard with API metrics | ✅ DONE |
| **CloudWatch Alarms** | High latency, 5xx errors, Lambda errors alerts | ✅ DONE |
| **CloudFront Access Logging** | Request logs to S3 for troubleshooting | ✅ DONE |
| **Analysis Management UI** | Split-pane markdown editor with live preview | ✅ DONE |
| **Collection Statistics Dashboard** | Charts: value growth, bindery, era, publishers | ✅ DONE |
| **Image Upload/Delete** | Upload and delete images from book detail | ✅ DONE |
| **User Profile Names** | Editable first/last name on profiles | ✅ DONE |
| **Insurance Report View** | Print-optimized with CSV export | ✅ DONE |

---

## Infrastructure & Resiliency

**Context:** Internal family use only, not public-facing. Prioritize cost over high availability.

### Current Architecture

```text
CloudFront → S3 (Frontend)
CloudFront → API Gateway → Lambda → Aurora Serverless v2
                                  → AWS Bedrock (Opus/Sonnet/Haiku)
                                  → S3 (Images + Prompts + Portraits)
                                  → SQS (Analysis + Profile Generation)
```

**Dual Environment:** Production (`app.bluemoxon.com`) and Staging (`staging.app.bluemoxon.com`) with isolated Cognito pools, databases, and S3 buckets.

### Rollback Capabilities

| Component | Current State | Recommendation | Cost Impact | Status |
|-----------|---------------|----------------|-------------|--------|
| **Lambda** | Versioning + prod alias | Keep last 3 versions | +$0/month (free tier) | DONE |
| **Frontend (S3)** | Versioning enabled | 30-day lifecycle rule | +$0.50-1/month | DONE |
| **Database** | Daily snapshots | Keep current (Aurora auto-snapshots free) | $0 | DONE |
| **Infrastructure** | CDK deployed | Document manual rollback procedures | $0 | DONE |

**Rollback documentation:** See [ROLLBACK.md](./ROLLBACK.md) for procedures.

### Recommended Rollback Strategy (Budget-Conscious)

#### 1. Lambda Versioning (~$0 additional)

```bash
# Enable in CDK or manually:
aws lambda publish-version --function-name bluemoxon-api

# Create alias for production
aws lambda create-alias \
  --function-name bluemoxon-api \
  --name prod \
  --function-version 1

# Rollback by updating alias
aws lambda update-alias \
  --function-name bluemoxon-api \
  --name prod \
  --function-version <previous-version>
```

**Implementation:**

- Publish version after each deployment
- Keep last 3 versions (auto-cleanup older)
- Update alias instead of function directly

#### 2. S3 Frontend Versioning (~$0.50-1/month)

```bash
# Enable versioning on bucket
aws s3api put-bucket-versioning \
  --bucket bluemoxon-frontend \
  --versioning-configuration Status=Enabled

# Rollback: restore previous version of index.html and assets
aws s3api list-object-versions --bucket bluemoxon-frontend --prefix index.html
```

**Implementation:**

- Enable versioning on `bluemoxon-frontend` bucket
- Set lifecycle rule to delete versions older than 30 days
- Document rollback procedure

#### 3. Database Rollback (Current - Free)

- Aurora Serverless v2 includes automated backups (7-day retention)
- Point-in-time recovery available
- For major changes: manual snapshot before deployment

```bash
# Create manual snapshot before risky deploys
aws rds create-db-cluster-snapshot \
  --db-cluster-identifier bluemoxon-db \
  --db-cluster-snapshot-identifier pre-deploy-$(date +%Y%m%d)
```

#### 4. Infrastructure (Terraform) Rollback ($0)

Terraform state enables rollback:

- Git revert to previous Terraform code
- Run `terraform apply` with previous version
- State file tracks all resources for recovery

### NOT Recommended (Too Expensive for Internal Use)

| Feature | Why Not | Monthly Cost |
|---------|---------|--------------|
| Multi-AZ Aurora | Single user, downtime acceptable | +$30-50/month |
| Lambda Provisioned Concurrency | Cold starts acceptable | +$15-30/month |
| Route 53 Health Checks | Manual monitoring sufficient | +$1-2/month |
| AWS Backup Service | Aurora snapshots sufficient | +$5-10/month |

### Monitoring & Observability

| Feature | Description | Status |
|---------|-------------|--------|
| **CloudWatch Dashboard** | `BlueMoxon-API` - API latency, errors, Lambda metrics, CloudFront stats | ✅ DONE |
| **CloudWatch Alarms** | High latency (p99>3s), 5xx errors (>5), Lambda errors (>=1) | ✅ DONE |
| **CloudFront Access Logs** | Request logs to `bluemoxon-logs/cloudfront/` | ✅ DONE |
| **Health Check Endpoints** | `/health/live`, `/ready`, `/deep`, `/info` | ✅ DONE |
| **Staging Environment** | Full dual-environment with isolated resources | ✅ DONE |
| **SNS Notifications** | Alert notifications via email/SMS | Planned |
| **RDS Aurora Pause** | Schedule staging pause during off-hours (#477) | Planned |
| **Bedrock VPC Endpoint** | Eliminate NAT Gateway dependency (#476) | Planned |

**Dashboard URL:** <https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#dashboards:name=BlueMoxon-API>

---

## Frontend Performance

### Current State

- Vue 3 SPA served via CloudFront
- Route-based code splitting configured
- Thumbnail generation (300x300 JPEG) on upload
- CloudFront cache headers configured in deploy workflow
- DNS preconnect hints for API/S3/Cognito
- Bundle analysis available via `npm run bundle:analyze`

### Recommendations (Cost-Conscious)

| Improvement | Description | Effort | Cost | Status |
|-------------|-------------|--------|------|--------|
| **Route-based Code Splitting** | Lazy load views with dynamic imports | Low | $0 | DONE |
| **Image Optimization** | Generate thumbnails at upload time | Medium | $0 | DONE |
| **CloudFront Caching Headers** | Set proper Cache-Control on S3 objects | Low | $0 | DONE |
| **Preconnect DNS** | Add `<link rel="preconnect">` for API domain | Low | $0 | DONE |
| **Bundle Analysis** | Use `rollup-plugin-visualizer` to identify bloat | Low | $0 | DONE |

#### 1. Route-based Code Splitting

```typescript
// router/index.ts - change from:
import BookDetailView from '@/views/BookDetailView.vue'

// to:
const BookDetailView = () => import('@/views/BookDetailView.vue')
```

#### 2. Image Thumbnails at Upload

- Generate 200x200 thumbnail when image uploaded
- Store as separate S3 key: `books/{id}/thumb_{filename}`
- Use thumbnail in list views, full image in detail

#### 3. CloudFront Cache Headers

```bash
# Set cache headers on S3 objects during deploy
aws s3 sync dist/ s3://bluemoxon-frontend/ \
  --cache-control "public, max-age=31536000" \
  --exclude "index.html"

aws s3 cp dist/index.html s3://bluemoxon-frontend/ \
  --cache-control "no-cache, no-store, must-revalidate"
```

### NOT Recommended (Overkill for Internal Use)

| Feature | Why Not |
|---------|---------|
| Lambda@Edge image processing | Complex setup, cold starts, +$5-10/month |
| CloudFront Functions | Simple caching sufficient |
| Service Worker caching | Small user base, not needed |

---

## CI/CD Improvements

### Current State

- GitHub Actions CI with SAST, dependency scanning, secret detection
- Deploy workflow pushes to Lambda + S3
- ~4 minute total pipeline time
- **Deep health check validation** after deployment (DB, S3, Cognito, config)
- **Smoke tests** validate API endpoints, frontend, and image CDN
- Release tagging on successful deploy (`v{date}-{sha}`)

### Speed Improvements (Free)

| Improvement | Current | After | Effort | Status |
|-------------|---------|-------|--------|--------|
| **Parallel Jobs** | Sequential | Parallel lint/test/typecheck | Low | DONE |
| **Dependency Caching** | Basic | Aggressive caching | Low | DONE |
| **Conditional Deploys** | Always deploy | Only on changes to relevant paths | Medium | DONE |
| **Skip CI on Docs** | Runs on all commits | Skip for .md files | Low | DONE |

#### 1. Parallel Job Optimization

Already implemented - lint, test, typecheck run in parallel.

#### 2. Aggressive Caching

```yaml
# Already using Poetry cache, add npm cache optimization
- name: Cache npm
  uses: actions/cache@v4
  with:
    path: ~/.npm
    key: npm-${{ runner.os }}-${{ hashFiles('frontend/package-lock.json') }}
    restore-keys: npm-${{ runner.os }}-
```

#### 3. Path-based Conditional Deploys

```yaml
# Only deploy backend if backend files changed
deploy-backend:
  if: |
    contains(github.event.head_commit.modified, 'backend/') ||
    contains(github.event.head_commit.added, 'backend/')
```

#### 4. Skip CI for Documentation

```yaml
# In ci.yml
on:
  push:
    branches: [main]
    paths-ignore:
      - '**.md'
      - 'docs/**'
```

### Feature Improvements

| Feature | Description | Effort | Cost | Status |
|---------|-------------|--------|------|--------|
| ~~**Release Tags**~~ | ~~Auto-tag releases on main deploy~~ | ~~Low~~ | ~~$0~~ | ✅ DONE |
| ~~**Deep Health Check Smoke Tests**~~ | ~~Validate DB/S3/Cognito after deploy, fail on unhealthy~~ | ~~Medium~~ | ~~$0~~ | ✅ DONE |
| ~~**Image CDN Validation**~~ | ~~Verify CloudFront returns actual images, not error pages~~ | ~~Low~~ | ~~$0~~ | ✅ DONE |
| **Deployment Notifications** | Slack/email on deploy success/failure | Low | $0 | Planned |
| **Preview Environments** | PR previews (expensive, skip for internal) | High | +$10-20/month | Not planned |
| **Automated Dependency Updates** | Dependabot already configured | Done | $0 | DONE |

#### Release Tagging

```yaml
# Add to deploy.yml after successful deploy
- name: Create Release Tag
  run: |
    VERSION=$(date +%Y.%m.%d)-$(echo ${{ github.sha }} | head -c 7)
    git tag -a "v$VERSION" -m "Release $VERSION"
    git push origin "v$VERSION"
```

### NOT Recommended (Too Expensive/Complex)

| Feature | Why Not | Cost |
|---------|---------|------|
| Self-hosted Runners | GitHub free tier sufficient | +$20-50/month |
| AWS CodePipeline | GitHub Actions simpler | +$1-5/month |
| Preview Environments | Internal use, staging not needed | +$10-20/month |
| Canary Deployments | Single user, not needed | Complex |

---

## Priority Matrix

### High Priority (Do Soon)

| Item | Category | Effort | Impact | Status |
|------|----------|--------|--------|--------|
| Lambda Versioning | Infrastructure | Low | High (rollback capability) | DONE |
| S3 Versioning | Infrastructure | Low | High (rollback capability) | DONE |
| Route-based Code Splitting | Frontend | Low | Medium (faster loads) | DONE |
| CloudFront Cache Headers | Frontend | Low | Medium (faster loads) | DONE |

### Medium Priority (Do When Time Permits)

| Item | Category | Effort | Impact | Status |
|------|----------|--------|--------|--------|
| ~~AI-Discovered Connections (#1803)~~ | ~~Features~~ | ~~High~~ | ~~High (reveals hidden relationships)~~ | ✅ Complete |
| Social Circles Phase 2 | Features | High | Medium (search, stats, polish) | In Progress |
| ~~Thumbnail Generation~~ | Features | ~~Medium~~ | ~~Medium (faster list views)~~ | ✅ DONE |
| ~~Book Status Management UI~~ | Features | ~~Low~~ | ~~Medium (workflow improvement)~~ | ✅ DONE |
| ~~Advanced Filtering~~ | Features | ~~Medium~~ | ~~Medium (usability)~~ | ✅ DONE |
| ~~Image Gallery Lightbox~~ | Features | ~~Low~~ | ~~Medium (UX improvement)~~ | ✅ DONE |
| ~~Vitest Frontend Tests~~ | Testing | ~~Medium~~ | ~~Medium (code quality)~~ | ✅ DONE |
| ~~Analysis Management UI~~ | ~~Features~~ | ~~Medium~~ | ~~Medium (content editing)~~ | ✅ DONE |
| ~~Collection Statistics Dashboard~~ | Features | ~~Medium~~ | ~~Medium (insights)~~ | ✅ DONE |

### Low Priority (Nice to Have)

| Item | Category | Effort | Impact | Status |
|------|----------|--------|--------|--------|
| Literary London 1850 | Features | High | High (unique differentiator) | Vision |
| ~~Role-Based Authorization~~ | ~~Features~~ | ~~Medium~~ | ~~Low (single admin)~~ | ✅ DONE |
| Audit Logging | Features | Medium | Low (internal use) | |
| ~~Playwright E2E Tests~~ | Testing | ~~High~~ | ~~Low (manual testing OK)~~ | ✅ Configured |
| ~~Insurance/Export Reports~~ | Features | ~~High~~ | ~~Low (occasional need)~~ | ✅ DONE |
| Add Images to Insurance Report | Features | Low | Low (occasional need) | |
| ~~Mobile Responsive~~ | ~~Features~~ | ~~Medium~~ | ~~Low (desktop primary)~~ | ✅ DONE |

---

## Cost Summary

### Current Monthly Cost: ~$28-52

| Service | Current Cost |
|---------|--------------|
| Aurora Serverless v2 | $15-25 |
| Lambda + API Gateway | $1-3 |
| S3 (frontend + images + logs) | $2-4 |
| CloudFront | $2-5 |
| CloudWatch (dashboard + alarms) | $1-3 |
| Route 53 + domain | $1-2 |
| Secrets Manager | $1 |
| NAT Gateway | $5-10 |

### Recently Added (Included Above)

| Addition | Cost |
|----------|------|
| S3 Versioning | +$0.50-1/month |
| Lambda Versioning | $0 (free tier) |
| CloudWatch Dashboard | ~$3/month |
| CloudWatch Alarms (3) | ~$0.30/month |
| CloudFront Access Logs | ~$0.50/month |
| **Current Total** | **~$28-52/month** |

### Staying Under $50/month

To stay within budget:

- Keep Aurora Serverless v2 at minimum ACU (0.5)
- Avoid provisioned concurrency
- Use aggressive S3 lifecycle rules (delete old versions after 30 days)
- Avoid multi-region deployments

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [Architecture](ARCHITECTURE.md) | Current system design |
| [Features](FEATURES.md) | Implemented features catalog |
| [Bedrock](BEDROCK.md) | AI analysis integration (Napoleon Framework) |
| [Operations](OPERATIONS.md) | Runbook for common operations |
| [Eval Runbook Scaling](EVAL_RUNBOOK_SCALING.md) | Multi-tenant scaling roadmap |
| [Victorian Social Circles Design](plans/2026-01-26-victorian-social-circles-design.md) | Social circles network visualization |
| [AI-Discovered Connections Design](plans/2026-02-04-ai-discovered-connections-design.md) | Personal connections via AI discovery |
| [AI Connections Implementation Plan](plans/2026-02-04-ai-connections-implementation-plan.md) | Implementation tasks for #1803 |

---

**Last Updated:** 2026-02-06
