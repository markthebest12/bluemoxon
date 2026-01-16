# Performance Documentation

## Overview

BlueMoxon is optimized for fast load times and excellent Core Web Vitals scores. This document covers performance metrics, optimization strategies, and testing procedures.

## Current Performance Metrics

Measured via Playwright against production (bluemoxon.com):

| Page | FCP | LCP | DCL | Transfer Size |
|------|-----|-----|-----|---------------|
| Home | ~1.0s | ~1.0s | ~500ms | 81 KB |
| Books List | ~950ms | ~950ms | ~550ms | 81 KB |
| Book Detail | ~970ms | ~970ms | ~530ms | 81 KB |

### Core Web Vitals Targets (Google)

| Metric | Good | Needs Improvement | Poor | BlueMoxon |
|--------|------|-------------------|------|-----------|
| **FCP** (First Contentful Paint) | < 1.8s | < 3.0s | > 3.0s | ✅ ~1.0s |
| **LCP** (Largest Contentful Paint) | < 2.5s | < 4.0s | > 4.0s | ✅ ~1.0s |
| **CLS** (Cumulative Layout Shift) | < 0.1 | < 0.25 | > 0.25 | ✅ Minimal |

## Recent Optimizations (January 2026)

### App Shell Architecture (#876)

- Skeleton loading shows immediately while data loads
- Improved perceived performance on initial page load
- CSS-only skeletons (no JavaScript blocking)

### Dashboard API Batching (#877, #878)

- Consolidated 6 dashboard API calls into single `/dashboard/batch` endpoint
- Reduced network round trips from 6 to 1
- ~40% faster dashboard load time

### Vue 3 Composables (#879)

- `useDashboardCache` - Client-side caching with 5-minute TTL
- `useCurrencyConversion` - Memoized currency calculations
- `useToast` - Centralized notification management
- Reduced redundant API calls and computations

### BookDetailView Refactor (#807)

- Split monolithic component into focused sub-components
- Improved code splitting and lazy loading
- Better memory management for image galleries

---

## Optimization Strategies

### 1. Code Splitting

Vite automatically splits the bundle into chunks for better caching:

```text
dist/assets/
├── vue-vendor-*.js      # Vue, Vue Router, Pinia (103 KB)
├── aws-auth-*.js        # AWS Amplify auth (127 KB)
├── api-*.js             # Axios + API service (37 KB)
├── index-*.js           # App shell (8 KB)
├── BooksView-*.js       # Books page (9 KB, lazy)
├── BookDetailView-*.js  # Detail page (12 KB, lazy)
└── ...other views       # Lazy loaded
```

Configuration in `vite.config.ts`:

```typescript
manualChunks: (id) => {
  if (id.includes('node_modules/vue') ||
      id.includes('node_modules/vue-router') ||
      id.includes('node_modules/pinia')) {
    return 'vue-vendor'
  }
  if (id.includes('node_modules/aws-amplify')) {
    return 'aws-auth'
  }
}
```

### 2. Image Optimization

- **Thumbnails**: 300x300 JPEG @ 85% quality (~10-20 KB each)
- **Lazy Loading**: Images load on scroll into viewport
- **S3 + CloudFront**: Images served via CDN with caching

Thumbnail generation:

```python
# backend/app/api/v1/images.py
THUMBNAIL_SIZE = (300, 300)
THUMBNAIL_QUALITY = 85
```

### 3. Caching Strategy

**CloudFront Cache Headers:**

- Static assets (JS/CSS): 1 year cache (hashed filenames)
- HTML: No cache (always fresh)
- Images: 1 day cache
- API responses: No cache

**Browser Caching:**

- Service worker not implemented (future consideration)
- Local storage for auth tokens only

### 4. Bundle Size Budget

Current totals (gzipped):

- **Total JS**: ~285 KB
- **Total CSS**: ~4.5 KB
- **Per-page overhead**: ~81 KB (initial load)

Vite warning threshold: 500 KB per chunk

## Running Performance Tests

### Automated Tests (Playwright)

```bash
# Run all performance tests
npm run test:e2e -- e2e/performance.spec.ts

# Run with specific browser
npm run test:e2e -- e2e/performance.spec.ts --project=chromium

# Run with visible browser
npm run test:e2e -- e2e/performance.spec.ts --headed
```

### Manual Testing

**Chrome DevTools:**

1. Open DevTools → Network tab
2. Enable "Disable cache"
3. Throttle to "Fast 3G" for realistic mobile testing
4. Reload and observe waterfall

**Lighthouse:**

1. Open DevTools → Lighthouse tab
2. Select "Performance" category
3. Choose "Mobile" or "Desktop"
4. Click "Analyze page load"

**WebPageTest:**

- URL: <https://www.webpagetest.org/>
- Test from multiple locations
- Compare filmstrip views

## Performance Monitoring

### Current Setup

- No APM tool configured
- Manual testing via Playwright
- Bundle analyzer: `npm run bundle:analyze`

### Recommended Future Additions

1. **Real User Monitoring (RUM)**
   - Consider: Vercel Analytics, Plausible, or custom
2. **Synthetic Monitoring**
   - Consider: Checkly, Datadog Synthetics
3. **Error Tracking**
   - Consider: Sentry (already lightweight)

## Optimization Opportunities

### Implemented ✅

- [x] Code splitting (Vue vendor, AWS auth)
- [x] Image thumbnails (300x300)
- [x] Lazy loading routes
- [x] CloudFront CDN
- [x] Gzip compression
- [x] ES2020 target (smaller bundles)

### Future Considerations

- [ ] Service worker for offline support
- [ ] Preload critical resources
- [ ] HTTP/2 server push
- [ ] Image format optimization (WebP/AVIF)
- [ ] Critical CSS inlining
- [ ] Skeleton loading states

## Troubleshooting

### Slow Initial Load

1. Check network tab for blocking resources
2. Verify CloudFront is serving cached assets
3. Check Lambda cold start times (API)

### Large Bundle Size

1. Run `npm run bundle:analyze`
2. Check `stats.html` for largest modules
3. Consider lazy loading large dependencies

### Slow API Responses

1. Check Lambda logs in CloudWatch
2. Verify database query performance
3. Consider adding API response caching

## Related Files

- `vite.config.ts` - Build optimization settings
- `frontend/e2e/performance.spec.ts` - Automated performance tests
- `backend/app/api/v1/images.py` - Thumbnail generation
- `scripts/generate_thumbnails.py` - Batch thumbnail generation
