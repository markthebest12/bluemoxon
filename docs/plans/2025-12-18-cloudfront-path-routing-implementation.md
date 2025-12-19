# CloudFront Path-Based Routing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Route `/book-images/*` requests to the images S3 bucket via CloudFront Function path rewriting.

**Architecture:** Add secondary origin (images bucket) and ordered cache behavior to frontend CloudFront distribution. CloudFront Function strips `/book-images` prefix before forwarding to S3. Both staging and prod use OAC for authentication.

**Tech Stack:** Terraform, AWS CloudFront, CloudFront Functions (cloudfront-js-2.0)

---

## Task 1: Add CloudFront Function Resource

**Files:**
- Modify: `infra/terraform/modules/cloudfront/main.tf`

**Step 1: Add CloudFront Function resource after OAC block (around line 34)**

Add this resource:

```hcl
# -----------------------------------------------------------------------------
# CloudFront Function for Path Rewriting (Secondary Origin)
# -----------------------------------------------------------------------------

resource "aws_cloudfront_function" "path_rewrite" {
  count   = var.secondary_origin_path_pattern != null ? 1 : 0
  name    = "${var.s3_bucket_name}-path-rewrite"
  runtime = "cloudfront-js-2.0"
  publish = true
  code    = <<-EOF
function handler(event) {
    var request = event.request;
    var uri = request.uri;

    // Strip /book-images prefix
    if (uri.startsWith('/book-images/')) {
        request.uri = uri.substring(12);
    }

    return request;
}
EOF
}
```

**Step 2: Validate syntax**

Run: `cd infra/terraform && terraform fmt -check modules/cloudfront/main.tf`
Expected: No output (file is formatted)

**Step 3: Commit**

```bash
git add infra/terraform/modules/cloudfront/main.tf
git commit -m "feat(cloudfront): add CloudFront Function for path rewriting (#430)"
```

---

## Task 2: Add Secondary OAC Resource

**Files:**
- Modify: `infra/terraform/modules/cloudfront/main.tf`

**Step 1: Add secondary OAC resource after the path_rewrite function**

Add this resource:

```hcl
# -----------------------------------------------------------------------------
# Origin Access Control (OAC) for Secondary Origin
# -----------------------------------------------------------------------------

resource "aws_cloudfront_origin_access_control" "secondary" {
  count                             = var.secondary_origin_bucket_name != null ? 1 : 0
  name                              = "${var.secondary_origin_bucket_name}-oac"
  description                       = "OAC for secondary S3 bucket access"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}
```

**Step 2: Validate syntax**

Run: `cd infra/terraform && terraform fmt modules/cloudfront/main.tf`
Expected: File formatted (or no changes if already correct)

**Step 3: Commit**

```bash
git add infra/terraform/modules/cloudfront/main.tf
git commit -m "feat(cloudfront): add secondary OAC for images bucket (#430)"
```

---

## Task 3: Add Secondary Origin Block

**Files:**
- Modify: `infra/terraform/modules/cloudfront/main.tf`

**Step 1: Add dynamic secondary origin block inside aws_cloudfront_distribution**

Find the closing brace of the first `origin` block (around line 57) and add:

```hcl
  dynamic "origin" {
    for_each = var.secondary_origin_bucket_name != null ? [1] : []
    content {
      domain_name              = var.secondary_origin_bucket_domain_name
      origin_id                = "S3-${var.secondary_origin_bucket_name}"
      origin_access_control_id = aws_cloudfront_origin_access_control.secondary[0].id
    }
  }
```

**Step 2: Validate syntax**

Run: `cd infra/terraform && terraform fmt modules/cloudfront/main.tf`
Expected: File formatted

**Step 3: Commit**

```bash
git add infra/terraform/modules/cloudfront/main.tf
git commit -m "feat(cloudfront): add secondary origin for images bucket (#430)"
```

---

## Task 4: Add Ordered Cache Behavior

**Files:**
- Modify: `infra/terraform/modules/cloudfront/main.tf`

**Step 1: Add ordered_cache_behavior block after default_cache_behavior**

Find the closing brace of `default_cache_behavior` (around line 76) and add:

```hcl
  dynamic "ordered_cache_behavior" {
    for_each = var.secondary_origin_path_pattern != null ? [1] : []
    content {
      path_pattern           = var.secondary_origin_path_pattern
      allowed_methods        = ["GET", "HEAD", "OPTIONS"]
      cached_methods         = ["GET", "HEAD"]
      target_origin_id       = "S3-${var.secondary_origin_bucket_name}"
      viewer_protocol_policy = "redirect-to-https"
      compress               = true

      forwarded_values {
        query_string = false
        cookies {
          forward = "none"
        }
      }

      min_ttl     = 0
      default_ttl = var.secondary_origin_ttl
      max_ttl     = var.max_ttl

      function_association {
        event_type   = "viewer-request"
        function_arn = aws_cloudfront_function.path_rewrite[0].arn
      }
    }
  }
```

**Step 2: Validate syntax**

Run: `cd infra/terraform && terraform fmt modules/cloudfront/main.tf`
Expected: File formatted

**Step 3: Commit**

```bash
git add infra/terraform/modules/cloudfront/main.tf
git commit -m "feat(cloudfront): add ordered cache behavior for /book-images/* (#430)"
```

---

## Task 5: Add Secondary OAC Output

**Files:**
- Modify: `infra/terraform/modules/cloudfront/outputs.tf`

**Step 1: Add output for secondary OAC ID**

Add at end of file:

```hcl
output "secondary_oac_id" {
  description = "ID of the secondary Origin Access Control (for images bucket policy)"
  value       = length(aws_cloudfront_origin_access_control.secondary) > 0 ? aws_cloudfront_origin_access_control.secondary[0].id : null
}
```

**Step 2: Commit**

```bash
git add infra/terraform/modules/cloudfront/outputs.tf
git commit -m "feat(cloudfront): export secondary OAC ID (#430)"
```

---

## Task 6: Update Root main.tf to Pass Images Bucket Config

**Files:**
- Modify: `infra/terraform/main.tf`

**Step 1: Find the frontend_cdn module call (around line 86)**

Add secondary origin variables to the module call. Find:

```hcl
module "frontend_cdn" {
```

Add these lines inside the module block (after existing variables):

```hcl
  # Secondary origin for images (enables /book-images/* routing)
  secondary_origin_bucket_name        = var.secondary_origin_bucket_name
  secondary_origin_bucket_domain_name = var.secondary_origin_bucket_domain_name
  secondary_origin_path_pattern       = var.secondary_origin_path_pattern
  secondary_origin_ttl                = var.secondary_origin_ttl
```

**Step 2: Validate syntax**

Run: `cd infra/terraform && terraform fmt main.tf`
Expected: File formatted

**Step 3: Commit**

```bash
git add infra/terraform/main.tf
git commit -m "feat(terraform): pass images bucket config to frontend_cdn module (#430)"
```

---

## Task 7: Add Root Variables for Secondary Origin

**Files:**
- Modify: `infra/terraform/variables.tf`

**Step 1: Check if variables already exist**

Run: `grep -c "secondary_origin" infra/terraform/variables.tf`

If output is 0, add these variables. If > 0, skip to Step 3.

**Step 2: Add variables (if not present)**

Add at end of file:

```hcl
# =============================================================================
# Secondary Origin (Images Bucket) Configuration
# =============================================================================

variable "secondary_origin_bucket_name" {
  type        = string
  description = "Name of secondary S3 bucket for images (optional)"
  default     = null
}

variable "secondary_origin_bucket_domain_name" {
  type        = string
  description = "Regional domain name of secondary S3 bucket"
  default     = null
}

variable "secondary_origin_path_pattern" {
  type        = string
  description = "Path pattern for secondary origin (e.g., '/book-images/*')"
  default     = null
}

variable "secondary_origin_ttl" {
  type        = number
  description = "Default TTL for secondary origin cache behavior in seconds"
  default     = 604800
}
```

**Step 3: Commit**

```bash
git add infra/terraform/variables.tf
git commit -m "feat(terraform): add secondary origin variables (#430)"
```

---

## Task 8: Update staging.tfvars

**Files:**
- Modify: `infra/terraform/envs/staging.tfvars`

**Step 1: Add secondary origin configuration**

Add at end of file (before any closing comments):

```hcl
# =============================================================================
# Secondary Origin (Images Bucket) for /book-images/* routing
# =============================================================================
secondary_origin_bucket_name        = "bluemoxon-staging-images"
secondary_origin_bucket_domain_name = "bluemoxon-staging-images.s3.us-west-2.amazonaws.com"
secondary_origin_path_pattern       = "/book-images/*"
secondary_origin_ttl                = 604800
```

**Step 2: Commit**

```bash
git add infra/terraform/envs/staging.tfvars
git commit -m "feat(terraform): enable images path routing in staging (#430)"
```

---

## Task 9: Update prod.tfvars

**Files:**
- Modify: `infra/terraform/envs/prod.tfvars`

**Step 1: Add secondary origin configuration**

Add near the images_cdn_url_override line:

```hcl
# =============================================================================
# Secondary Origin (Images Bucket) for /book-images/* routing
# =============================================================================
secondary_origin_bucket_name        = "bluemoxon-images"
secondary_origin_bucket_domain_name = "bluemoxon-images.s3.us-west-2.amazonaws.com"
secondary_origin_path_pattern       = "/book-images/*"
secondary_origin_ttl                = 604800
```

**Step 2: Commit**

```bash
git add infra/terraform/envs/prod.tfvars
git commit -m "feat(terraform): enable images path routing in prod (#430)"
```

---

## Task 10: Deploy to Staging and Verify

**Step 1: Initialize Terraform for staging**

Run:
```bash
cd infra/terraform
AWS_PROFILE=bmx-staging terraform init -backend-config=backends/staging.conf
```

**Step 2: Plan staging changes**

Run:
```bash
AWS_PROFILE=bmx-staging terraform plan -var-file=envs/staging.tfvars -var="db_password=staging-dummy"
```

Expected: Plan shows:
- 1 CloudFront Function to add
- 1 OAC to add
- CloudFront distribution to update (new origin + cache behavior)

**Step 3: Apply to staging**

Run:
```bash
AWS_PROFILE=bmx-staging terraform apply -var-file=envs/staging.tfvars -var="db_password=staging-dummy"
```

**Step 4: Wait for CloudFront deployment (5-10 minutes)**

Run:
```bash
sleep 300
```

**Step 5: Verify path routing works**

Run:
```bash
curl -sI "https://staging.app.bluemoxon.com/book-images/books/10_0b810ca69dbd43f0b09dc51cd8785370.jpg" | grep -i content-type
```

Expected: `content-type: image/jpeg`

**Step 6: Commit terraform.lock if changed**

```bash
git add -A
git commit -m "chore: update terraform lock file" --allow-empty
```

---

## Task 11: Update Staging images_cdn_url_override

**Files:**
- Modify: `infra/terraform/envs/staging.tfvars`

**Step 1: Update images_cdn_url_override to branded URL**

Find and replace:
```hcl
images_cdn_url_override = "https://d2zwmzka4w6cws.cloudfront.net"
```

With:
```hcl
images_cdn_url_override = "https://staging.app.bluemoxon.com/book-images"
```

**Step 2: Apply to staging**

Run:
```bash
AWS_PROFILE=bmx-staging terraform apply -var-file=envs/staging.tfvars -var="db_password=staging-dummy"
```

**Step 3: Verify API returns branded URLs**

Run:
```bash
bmx-api GET '/books/1' | jq '.images'
```

Expected: URLs start with `https://staging.app.bluemoxon.com/book-images/`

**Step 4: Commit**

```bash
git add infra/terraform/envs/staging.tfvars
git commit -m "feat(terraform): use branded image URLs in staging (#430)"
```

---

## Task 12: Deploy to Production

**Step 1: Initialize Terraform for production**

Run:
```bash
cd infra/terraform
AWS_PROFILE=bmx-prod terraform init -backend-config=backends/prod.conf -reconfigure
```

**Step 2: Plan production changes**

Run:
```bash
AWS_PROFILE=bmx-prod terraform plan -var-file=envs/prod.tfvars -var="db_password=prod-dummy"
```

Expected: Same changes as staging

**Step 3: Apply to production**

Run:
```bash
AWS_PROFILE=bmx-prod terraform apply -var-file=envs/prod.tfvars -var="db_password=prod-dummy"
```

**Step 4: Wait for CloudFront deployment**

Run:
```bash
sleep 300
```

**Step 5: Verify path routing works**

Run:
```bash
curl -sI "https://app.bluemoxon.com/book-images/books/10_0b810ca69dbd43f0b09dc51cd8785370.jpg" | grep -i content-type
```

Expected: `content-type: image/jpeg`

---

## Task 13: Update Production images_cdn_url_override

**Files:**
- Modify: `infra/terraform/envs/prod.tfvars`

**Step 1: Update images_cdn_url_override to branded URL**

Find and replace:
```hcl
images_cdn_url_override = "https://d1yejmcspwgw9x.cloudfront.net"
```

With:
```hcl
images_cdn_url_override = "https://app.bluemoxon.com/book-images"
```

**Step 2: Apply to production**

Run:
```bash
AWS_PROFILE=bmx-prod terraform apply -var-file=envs/prod.tfvars -var="db_password=prod-dummy"
```

**Step 3: Verify API returns branded URLs**

Run:
```bash
bmx-api --prod GET '/books/1' | jq '.images'
```

Expected: URLs start with `https://app.bluemoxon.com/book-images/`

**Step 4: Commit**

```bash
git add infra/terraform/envs/prod.tfvars
git commit -m "feat(terraform): use branded image URLs in production (#430)"
```

---

## Task 14: Create PR and Merge

**Step 1: Push branch**

Run:
```bash
git push -u origin feat/cloudfront-path-routing
```

**Step 2: Create PR**

Run:
```bash
gh pr create --base staging --title "feat: Implement CloudFront path-based routing for images (#430)" --body "$(cat <<'EOF'
## Summary
- Adds `/book-images/*` cache behavior to frontend CloudFront
- CloudFront Function strips path prefix before S3 request
- Both staging and prod now serve images via branded URLs

## Changes
- CloudFront Function for path rewriting
- Secondary OAC for images bucket
- Secondary origin in CloudFront distribution
- Ordered cache behavior for `/book-images/*`

## Testing
- Staging verified: `https://staging.app.bluemoxon.com/book-images/...` returns images
- Production verified: `https://app.bluemoxon.com/book-images/...` returns images

Closes #430

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

**Step 3: Wait for CI and merge**

Run:
```bash
gh pr checks --watch
gh pr merge --squash --delete-branch
```

---

## Acceptance Criteria Verification

After all tasks complete, verify:

- [ ] `curl -sI "https://staging.app.bluemoxon.com/book-images/books/X.jpg" | grep content-type` returns `image/jpeg`
- [ ] `curl -sI "https://app.bluemoxon.com/book-images/books/X.jpg" | grep content-type` returns `image/jpeg`
- [ ] API responses use branded image URLs
- [ ] No manual CloudFront changes required
