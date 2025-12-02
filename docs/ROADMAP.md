# BlueMoxon Feature Roadmap

This document tracks planned features, improvements, and technical debt for the BlueMoxon Victorian Book Collection application.

**Target Budget:** $40-50/month (internal family use only)

---

## Table of Contents

1. [Application Features](#application-features)
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
| **Role-Based Authorization** | Architecture defines admin/editor/viewer roles; `users.role` field exists but not enforced in API | Low | Medium | |
| ~~**Book Status Management**~~ | ~~Color-coded dropdown selector on book detail page (ON_HAND, IN_TRANSIT, SOLD, REMOVED)~~ | ~~Medium~~ | ~~Low~~ | ✅ DONE |
| ~~**Provenance Tracking**~~ | ~~View/edit modes for ownership history, inscriptions, bookplates~~ | ~~Low~~ | ~~Low~~ | ✅ DONE |
| **Analysis Management UI** | `book_analyses` table exists but no frontend UI to create/edit (only read from import) | Medium | Medium | |
| ~~**Image Gallery Lightbox**~~ | ~~Full-screen image viewer on book detail~~ | ~~Medium~~ | ~~Low~~ | ✅ DONE |
| ~~**Image Drag-and-Drop Reordering**~~ | ~~Drag-and-drop interface for reordering images with display_order persistence~~ | ~~Low~~ | ~~Medium~~ | ✅ DONE |
| ~~**Advanced Filtering**~~ | ~~Filter panel: bindery, publisher, tier, binding type, condition, status, year/value range~~ | ~~Medium~~ | ~~Medium~~ | ✅ DONE |
| ~~**Filter State Persistence**~~ | ~~Filter state preserved on back navigation and "Back to Collection" link~~ | ~~Low~~ | ~~Low~~ | ✅ DONE |

### New Feature Ideas

| Feature | Description | Priority | Effort | Status |
|---------|-------------|----------|--------|--------|
| ~~**Collection Statistics Dashboard**~~ | ~~Value growth chart, premium bindings distribution, era breakdown, top publishers~~ | ~~Medium~~ | ~~Medium~~ | ✅ DONE |
| ~~**Insurance/Export Reports**~~ | ~~Insurance valuation report with CSV export, report type selector (Primary/Extended/Full)~~ | ~~Low~~ | ~~High~~ | ✅ DONE |
| **PDF Catalog Generation** | Printable PDF catalog with images | Low | High | |
| **Audit Logging** | Track changes to book records (who changed what and when) | Low | Medium | |
| **Backup/Restore UI** | Database backup scheduling, export/import functionality | Low | Medium | |
| **Mobile Responsive Improvements** | Current UI is desktop-focused | Low | Medium | |

### Recently Completed (Not Previously Tracked)

| Feature | Description | Status |
|---------|-------------|--------|
| **Collection Statistics Dashboard** | Interactive charts: value growth, bindery distribution, era breakdown, top publishers | ✅ DONE |
| **Image Upload/Delete** | Upload new images and delete existing from book detail page | ✅ DONE |
| **User Profile Names** | Editable first/last name on user profiles | ✅ DONE |
| **Insurance Report View** | Browser-print optimized report with CSV export for Primary/Extended/Full inventory | ✅ DONE |

---

## Infrastructure & Resiliency

**Context:** Internal family use only, not public-facing. Prioritize cost over high availability.

### Current Architecture

```
CloudFront → S3 (Frontend)
CloudFront → API Gateway → Lambda → Aurora Serverless v2
```

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

#### 4. Infrastructure (CDK) Rollback ($0)
CDK doesn't have built-in rollback, but:
- Git revert to previous CDK code
- Run `cdk deploy` with previous version
- Document critical resource IDs for manual recovery

### NOT Recommended (Too Expensive for Internal Use)

| Feature | Why Not | Monthly Cost |
|---------|---------|--------------|
| Multi-AZ Aurora | Single user, downtime acceptable | +$30-50/month |
| Lambda Provisioned Concurrency | Cold starts acceptable | +$15-30/month |
| Route 53 Health Checks | Manual monitoring sufficient | +$1-2/month |
| AWS Backup Service | Aurora snapshots sufficient | +$5-10/month |

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
- ~3-5 minute total pipeline time

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
| **Deployment Notifications** | Slack/email on deploy success/failure | Low | $0 | Planned |
| **Preview Environments** | PR previews (expensive, skip for internal) | High | +$10-20/month | Not planned |
| **Automated Dependency Updates** | Dependabot already configured | Done | $0 | DONE |
| **Release Tags** | Auto-tag releases on main deploy | Low | $0 | DONE |

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
| ~~Thumbnail Generation~~ | Features | ~~Medium~~ | ~~Medium (faster list views)~~ | ✅ DONE |
| ~~Book Status Management UI~~ | Features | ~~Low~~ | ~~Medium (workflow improvement)~~ | ✅ DONE |
| ~~Advanced Filtering~~ | Features | ~~Medium~~ | ~~Medium (usability)~~ | ✅ DONE |
| ~~Image Gallery Lightbox~~ | Features | ~~Low~~ | ~~Medium (UX improvement)~~ | ✅ DONE |
| ~~Vitest Frontend Tests~~ | Testing | ~~Medium~~ | ~~Medium (code quality)~~ | ✅ DONE |
| Analysis Management UI | Features | Medium | Medium (content editing) | |
| ~~Collection Statistics Dashboard~~ | Features | ~~Medium~~ | ~~Medium (insights)~~ | ✅ DONE |

### Low Priority (Nice to Have)

| Item | Category | Effort | Impact | Status |
|------|----------|--------|--------|--------|
| Role-Based Authorization | Features | Medium | Low (single admin) | |
| Audit Logging | Features | Medium | Low (internal use) | |
| ~~Playwright E2E Tests~~ | Testing | ~~High~~ | ~~Low (manual testing OK)~~ | ✅ Configured |
| ~~Insurance/Export Reports~~ | Features | ~~High~~ | ~~Low (occasional need)~~ | ✅ DONE |
| PDF Catalog Generation | Features | High | Low (occasional need) | |
| Mobile Responsive | Features | Medium | Low (desktop primary) | |

---

## Cost Summary

### Current Monthly Cost: ~$27-49

| Service | Current Cost |
|---------|--------------|
| Aurora Serverless v2 | $15-25 |
| Lambda + API Gateway | $1-3 |
| S3 (frontend + images) | $2-3 |
| CloudFront | $2-5 |
| Route 53 + domain | $1-2 |
| Secrets Manager | $1 |
| NAT Gateway | $5-10 |

### Recommended Additions: +$0.50-1

| Addition | Cost |
|----------|------|
| S3 Versioning | +$0.50-1/month |
| Lambda Versioning | $0 (free tier) |
| **New Total** | **~$28-50/month** |

### Staying Under $50/month

To stay within budget:
- Keep Aurora Serverless v2 at minimum ACU (0.5)
- Avoid provisioned concurrency
- Use aggressive S3 lifecycle rules (delete old versions after 30 days)
- Avoid multi-region deployments

---

**Last Updated:** 2025-12-02
