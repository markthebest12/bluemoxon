# CloudFront Path-Based Routing for Images

**Issue:** #430
**Date:** 2025-12-18
**Status:** Design Complete

## Problem

The Lambda returns branded image URLs (`https://app.bluemoxon.com/book-images/...`) but CloudFront has no cache behavior for this path. Requests return the SPA's `index.html` instead of images.

**Current workaround:** Direct CloudFront domains (`d1yejmcspwgw9x.cloudfront.net`)

## Solution

Add secondary origin and cache behavior to the frontend CloudFront distribution.

## Architecture

```
Request: /book-images/books/123.jpg
         │
         ▼
┌─────────────────────────────────────────────────┐
│           CloudFront Distribution               │
│  (app.bluemoxon.com / staging.app.bluemoxon.com)│
├─────────────────────────────────────────────────┤
│  Cache Behaviors:                               │
│  ┌───────────────────────────────────────────┐  │
│  │ /book-images/*  → Images Origin           │  │
│  │   └─ CloudFront Function strips prefix    │  │
│  │   └─ OAC authenticates to S3              │  │
│  │   └─ 404s return actual 404               │  │
│  ├───────────────────────────────────────────┤  │
│  │ /* (default)    → Frontend Origin         │  │
│  │   └─ SPA routing (404→index.html)         │  │
│  └───────────────────────────────────────────┘  │
├─────────────────────────────────────────────────┤
│  Origins:                                       │
│  1. Frontend S3 bucket (existing)               │
│  2. Images S3 bucket (new secondary origin)     │
└─────────────────────────────────────────────────┘
         │
         ▼
    S3: books/123.jpg (prefix stripped)
```

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Path stripping | CloudFront Function | Free tier, sub-ms latency, simple JS |
| Origin auth | New OAC per environment | Clean separation, module owns its resources |
| 404 handling | Return actual 404 | Images should fail explicitly, frontend handles gracefully |
| Staging/prod parity | Both use OAC | Consistent testing, no environment-specific behavior |

## CloudFront Function

```javascript
function handler(event) {
    var request = event.request;
    var uri = request.uri;

    // Strip /book-images prefix
    if (uri.startsWith('/book-images/')) {
        request.uri = uri.substring(12); // Remove '/book-images'
    }

    return request;
}
```

- **Type:** `viewer-request` (runs before cache lookup)
- **Runtime:** `cloudfront-js-2.0`

## Terraform Changes

### Files to Modify

| File | Changes |
|------|---------|
| `modules/cloudfront/main.tf` | Add CloudFront Function, secondary OAC, secondary origin, ordered cache behavior |
| `modules/cloudfront/outputs.tf` | Export function ARN (optional) |
| `main.tf` (root) | Pass images bucket config to cloudfront module |
| `envs/prod.tfvars` | Enable secondary origin config |
| `envs/staging.tfvars` | Enable secondary origin config |

### New Resources

1. **CloudFront Function** - Path rewrite (conditional on `secondary_origin_path_pattern`)
2. **OAC for images** - Separate from frontend OAC (conditional on `secondary_origin_bucket_name`)
3. **Secondary origin** - Points to images S3 bucket
4. **Ordered cache behavior** - Matches `/book-images/*` pattern

### Environment Configuration

**prod.tfvars:**
```hcl
secondary_origin_bucket_name        = "bluemoxon-images"
secondary_origin_bucket_domain_name = "bluemoxon-images.s3.us-west-2.amazonaws.com"
secondary_origin_path_pattern       = "/book-images/*"
secondary_origin_ttl                = 604800  # 7 days
images_cdn_url_override             = "https://app.bluemoxon.com/book-images"
```

**staging.tfvars:**
```hcl
secondary_origin_bucket_name        = "bluemoxon-staging-images"
secondary_origin_bucket_domain_name = "bluemoxon-staging-images.s3.us-west-2.amazonaws.com"
secondary_origin_path_pattern       = "/book-images/*"
secondary_origin_ttl                = 604800
images_cdn_url_override             = "https://staging.app.bluemoxon.com/book-images"
```

## Rollout Strategy

1. Deploy Terraform (adds origin + cache behavior + function)
2. Verify `/book-images/*` path works manually
3. Update `images_cdn_url_override` to branded URL
4. Deploy again to update Lambda env var

## Acceptance Criteria

- [ ] `https://app.bluemoxon.com/book-images/books/X.jpg` returns `content-type: image/jpeg`
- [ ] `https://staging.app.bluemoxon.com/book-images/books/X.jpg` returns `content-type: image/jpeg`
- [ ] Terraform manages all changes (no manual CloudFront edits)

## Verification Commands

```bash
# Staging
curl -sI "https://staging.app.bluemoxon.com/book-images/books/10_0b810ca69dbd43f0b09dc51cd8785370.jpg" | grep content-type

# Production
curl -sI "https://app.bluemoxon.com/book-images/books/10_0b810ca69dbd43f0b09dc51cd8785370.jpg" | grep content-type
```

## Rollback Plan

Revert `images_cdn_url_override` to direct CloudFront domains:
- Production: `https://d1yejmcspwgw9x.cloudfront.net`
- Staging: `https://d2zwmzka4w6cws.cloudfront.net`

Images continue working immediately via direct URLs.
