# =============================================================================
# CloudFront Distribution Module
# =============================================================================
# Supports both OAI (legacy) and OAC (modern) origin access types.
# OAC is the recommended approach for new distributions.

locals {
  use_oai  = var.origin_access_type == "oai"
  use_oac  = var.origin_access_type == "oac"
  oac_name = var.oac_name != null ? var.oac_name : "${var.s3_bucket_name}-oac"
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

# When using CloudFront default certificate (no ACM), AWS doesn't allow setting minimum_protocol_version.
# Production deployments should always use ACM certificates (set in tfvars).
# nosemgrep: terraform.aws.security.aws-cloudfront-insecure-tls.aws-insecure-cloudfront-distribution-tls-version
resource "aws_cloudfront_distribution" "this" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = var.default_root_object
  aliases             = var.domain_aliases
  price_class         = var.price_class
  comment             = var.comment

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

  dynamic "origin" {
    for_each = var.secondary_origin_bucket_name != null ? [1] : []
    content {
      domain_name              = var.secondary_origin_bucket_domain_name
      origin_id                = "S3-${var.secondary_origin_bucket_name}"
      origin_access_control_id = aws_cloudfront_origin_access_control.secondary[0].id
    }
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${var.s3_bucket_name}"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = var.default_ttl
    max_ttl     = var.max_ttl
  }

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

  # SPA routing: serve index.html for 404s
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
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
