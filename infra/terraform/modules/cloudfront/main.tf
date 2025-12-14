# =============================================================================
# CloudFront Distribution Module
# =============================================================================
# Supports both OAI (legacy) and OAC (modern) origin access types.
# OAC is the recommended approach for new distributions.
# Supports optional secondary origin for multi-origin distributions (e.g., images bucket).

locals {
  use_oai                   = var.origin_access_type == "oai"
  use_oac                   = var.origin_access_type == "oac"
  oac_name                  = var.oac_name != null ? var.oac_name : "${var.s3_bucket_name}-oac"
  has_secondary_origin      = var.secondary_origin_bucket_name != null
  secondary_oac_name        = var.secondary_origin_oac_name != null ? var.secondary_origin_oac_name : "${var.secondary_origin_bucket_name}-oac"
  has_logging               = var.logging_bucket != null
  has_secondary_cf_function = var.secondary_origin_function_arn != null
}

# -----------------------------------------------------------------------------
# Origin Access Identity (OAI) - Legacy approach
# -----------------------------------------------------------------------------

resource "aws_cloudfront_origin_access_identity" "this" {
  count   = local.use_oai ? 1 : 0
  comment = var.oai_comment
}

# -----------------------------------------------------------------------------
# Origin Access Control (OAC) - Modern approach
# -----------------------------------------------------------------------------

resource "aws_cloudfront_origin_access_control" "this" {
  count                             = local.use_oac ? 1 : 0
  name                              = local.oac_name
  description                       = var.oac_description
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# Secondary origin OAC (for multi-origin distributions like images bucket)
resource "aws_cloudfront_origin_access_control" "secondary" {
  count                             = local.use_oac && local.has_secondary_origin ? 1 : 0
  name                              = local.secondary_oac_name
  description                       = var.secondary_origin_oac_description
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# When using CloudFront default certificate (no ACM), AWS doesn't allow setting minimum_protocol_version.
# Production deployments should always use ACM certificates (set in tfvars).
# nosemgrep: terraform.aws.security.aws-cloudfront-insecure-tls.aws-insecure-cloudfront-distribution-tls-version
resource "aws_cloudfront_distribution" "this" {
  enabled             = true
  is_ipv6_enabled     = true
  http_version        = var.http_version
  default_root_object = var.default_root_object
  aliases             = var.domain_aliases
  price_class         = var.price_class
  comment             = var.comment

  # Primary origin (frontend bucket)
  origin {
    domain_name              = var.s3_bucket_domain_name
    origin_id                = "S3-${var.s3_bucket_name}"
    origin_access_control_id = local.use_oac ? aws_cloudfront_origin_access_control.this[0].id : null

    dynamic "s3_origin_config" {
      for_each = local.use_oai ? [1] : []
      content {
        origin_access_identity = aws_cloudfront_origin_access_identity.this[0].cloudfront_access_identity_path
      }
    }
  }

  # Secondary origin (images bucket) - optional
  dynamic "origin" {
    for_each = local.has_secondary_origin ? [1] : []
    content {
      domain_name              = var.secondary_origin_bucket_domain_name
      origin_id                = "S3-${var.secondary_origin_bucket_name}"
      origin_access_control_id = local.use_oac ? aws_cloudfront_origin_access_control.secondary[0].id : null
    }
  }

  default_cache_behavior {
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    target_origin_id           = "S3-${var.s3_bucket_name}"
    viewer_protocol_policy     = "redirect-to-https"
    compress                   = true
    cache_policy_id            = var.cache_policy_id
    response_headers_policy_id = var.response_headers_policy_id

    min_ttl     = var.cache_policy_id != null ? null : 0
    default_ttl = var.cache_policy_id != null ? null : var.default_ttl
    max_ttl     = var.cache_policy_id != null ? null : var.max_ttl

    dynamic "forwarded_values" {
      for_each = var.cache_policy_id == null ? [1] : []
      content {
        query_string = false
        cookies {
          forward = "none"
        }
      }
    }
  }

  # Cache behavior for secondary origin (e.g., /book-images/*)
  dynamic "ordered_cache_behavior" {
    for_each = local.has_secondary_origin && var.secondary_origin_path_pattern != null ? [1] : []
    content {
      path_pattern               = var.secondary_origin_path_pattern
      allowed_methods            = ["GET", "HEAD"]
      cached_methods             = ["GET", "HEAD"]
      target_origin_id           = "S3-${var.secondary_origin_bucket_name}"
      viewer_protocol_policy     = "redirect-to-https"
      compress                   = true
      cache_policy_id            = var.cache_policy_id
      response_headers_policy_id = var.response_headers_policy_id

      dynamic "function_association" {
        for_each = local.has_secondary_cf_function ? [1] : []
        content {
          event_type   = "viewer-request"
          function_arn = var.secondary_origin_function_arn
        }
      }
    }
  }

  # SPA routing: serve index.html for 404s and 403s
  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = var.error_caching_min_ttl
  }

  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = var.error_caching_min_ttl
  }

  # Access logging (optional)
  dynamic "logging_config" {
    for_each = local.has_logging ? [1] : []
    content {
      bucket          = var.logging_bucket
      prefix          = var.logging_prefix
      include_cookies = false
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn            = var.acm_certificate_arn
    ssl_support_method             = var.acm_certificate_arn != null ? "sni-only" : null
    minimum_protocol_version       = var.acm_certificate_arn != null ? "TLSv1.2_2021" : null
    cloudfront_default_certificate = var.acm_certificate_arn == null
  }

  tags = var.tags
}
