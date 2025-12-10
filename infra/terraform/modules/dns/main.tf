# =============================================================================
# DNS Module - Route53 Hosted Zone and Records
# =============================================================================
# This module manages DNS infrastructure including:
# - Route53 hosted zone
# - CloudFront alias records (A/AAAA)
# - API Gateway alias records
# - ACM certificate DNS validation records

# =============================================================================
# Route53 Hosted Zone
# =============================================================================

resource "aws_route53_zone" "this" {
  name    = var.domain_name
  comment = var.zone_comment

  tags = var.tags
}

# =============================================================================
# CloudFront Records - Landing Site (bluemoxon.com, www.bluemoxon.com)
# =============================================================================

resource "aws_route53_record" "landing_a" {
  count = var.landing_cloudfront_domain_name != null ? 1 : 0

  zone_id = aws_route53_zone.this.zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = var.landing_cloudfront_domain_name
    zone_id                = var.landing_cloudfront_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "landing_aaaa" {
  count = var.landing_cloudfront_domain_name != null ? 1 : 0

  zone_id = aws_route53_zone.this.zone_id
  name    = var.domain_name
  type    = "AAAA"

  alias {
    name                   = var.landing_cloudfront_domain_name
    zone_id                = var.landing_cloudfront_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "www_a" {
  count = var.landing_cloudfront_domain_name != null ? 1 : 0

  zone_id = aws_route53_zone.this.zone_id
  name    = "www.${var.domain_name}"
  type    = "A"

  alias {
    name                   = var.landing_cloudfront_domain_name
    zone_id                = var.landing_cloudfront_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "www_aaaa" {
  count = var.landing_cloudfront_domain_name != null ? 1 : 0

  zone_id = aws_route53_zone.this.zone_id
  name    = "www.${var.domain_name}"
  type    = "AAAA"

  alias {
    name                   = var.landing_cloudfront_domain_name
    zone_id                = var.landing_cloudfront_zone_id
    evaluate_target_health = false
  }
}

# =============================================================================
# CloudFront Records - Frontend App (app.bluemoxon.com)
# =============================================================================

resource "aws_route53_record" "app_a" {
  count = var.app_cloudfront_domain_name != null ? 1 : 0

  zone_id = aws_route53_zone.this.zone_id
  name    = "app.${var.domain_name}"
  type    = "A"

  alias {
    name                   = var.app_cloudfront_domain_name
    zone_id                = var.app_cloudfront_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "app_aaaa" {
  count = var.app_cloudfront_domain_name != null ? 1 : 0

  zone_id = aws_route53_zone.this.zone_id
  name    = "app.${var.domain_name}"
  type    = "AAAA"

  alias {
    name                   = var.app_cloudfront_domain_name
    zone_id                = var.app_cloudfront_zone_id
    evaluate_target_health = false
  }
}

# =============================================================================
# CloudFront Records - Staging Frontend App (staging.app.bluemoxon.com)
# =============================================================================

resource "aws_route53_record" "staging_app_a" {
  count = var.staging_app_cloudfront_domain_name != null ? 1 : 0

  zone_id = aws_route53_zone.this.zone_id
  name    = "staging.app.${var.domain_name}"
  type    = "A"

  alias {
    name                   = var.staging_app_cloudfront_domain_name
    zone_id                = var.staging_app_cloudfront_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "staging_app_aaaa" {
  count = var.staging_app_cloudfront_domain_name != null ? 1 : 0

  zone_id = aws_route53_zone.this.zone_id
  name    = "staging.app.${var.domain_name}"
  type    = "AAAA"

  alias {
    name                   = var.staging_app_cloudfront_domain_name
    zone_id                = var.staging_app_cloudfront_zone_id
    evaluate_target_health = false
  }
}

# =============================================================================
# API Gateway Records (api.bluemoxon.com)
# =============================================================================

resource "aws_route53_record" "api_a" {
  count = var.api_domain_name != null ? 1 : 0

  zone_id = aws_route53_zone.this.zone_id
  name    = "api.${var.domain_name}"
  type    = "A"

  alias {
    name                   = var.api_domain_name
    zone_id                = var.api_domain_zone_id
    evaluate_target_health = false
  }
}

# =============================================================================
# API Gateway Records - Staging (staging.api.bluemoxon.com)
# =============================================================================

resource "aws_route53_record" "staging_api_a" {
  count = var.staging_api_domain_name != null ? 1 : 0

  zone_id = aws_route53_zone.this.zone_id
  name    = "staging.api.${var.domain_name}"
  type    = "A"

  alias {
    name                   = var.staging_api_domain_name
    zone_id                = var.staging_api_domain_zone_id
    evaluate_target_health = false
  }
}
