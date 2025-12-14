output "distribution_arn" {
  description = "ARN of the CloudFront distribution"
  value       = aws_cloudfront_distribution.this.arn
}

output "distribution_domain_name" {
  description = "Domain name of the CloudFront distribution"
  value       = aws_cloudfront_distribution.this.domain_name
}

output "distribution_id" {
  description = "ID of the CloudFront distribution"
  value       = aws_cloudfront_distribution.this.id
}

output "distribution_hosted_zone_id" {
  description = "Route53 hosted zone ID for the CloudFront distribution"
  value       = aws_cloudfront_distribution.this.hosted_zone_id
}

# -----------------------------------------------------------------------------
# OAI Outputs (when origin_access_type = "oai")
# -----------------------------------------------------------------------------

output "oai_arn" {
  description = "ARN of the Origin Access Identity (null if using OAC)"
  value       = length(aws_cloudfront_origin_access_identity.this) > 0 ? aws_cloudfront_origin_access_identity.this[0].iam_arn : null
}

output "oai_path" {
  description = "CloudFront access identity path (null if using OAC)"
  value       = length(aws_cloudfront_origin_access_identity.this) > 0 ? aws_cloudfront_origin_access_identity.this[0].cloudfront_access_identity_path : null
}

# -----------------------------------------------------------------------------
# OAC Outputs (when origin_access_type = "oac")
# -----------------------------------------------------------------------------

output "oac_id" {
  description = "ID of the Origin Access Control (null if using OAI)"
  value       = length(aws_cloudfront_origin_access_control.this) > 0 ? aws_cloudfront_origin_access_control.this[0].id : null
}

output "oac_etag" {
  description = "ETag of the Origin Access Control (null if using OAI)"
  value       = length(aws_cloudfront_origin_access_control.this) > 0 ? aws_cloudfront_origin_access_control.this[0].etag : null
}

# -----------------------------------------------------------------------------
# S3 Bucket Policy Statement (for use by calling module)
# -----------------------------------------------------------------------------

output "s3_bucket_policy_statement_oac" {
  description = "S3 bucket policy statement for OAC access (JSON encoded, null if using OAI)"
  value = var.s3_bucket_arn != null && var.origin_access_type == "oac" ? jsonencode({
    Sid    = "AllowCloudFrontServicePrincipal"
    Effect = "Allow"
    Principal = {
      Service = "cloudfront.amazonaws.com"
    }
    Action   = "s3:GetObject"
    Resource = "${var.s3_bucket_arn}/*"
    Condition = {
      StringEquals = {
        "AWS:SourceArn" = aws_cloudfront_distribution.this.arn
      }
    }
  }) : null
}

output "s3_bucket_policy_statement_oai" {
  description = "S3 bucket policy statement for OAI access (JSON encoded, null if using OAC)"
  value = var.s3_bucket_arn != null && var.origin_access_type == "oai" ? jsonencode({
    Sid    = "AllowCloudFrontOAI"
    Effect = "Allow"
    Principal = {
      CanonicalUser = aws_cloudfront_origin_access_identity.this[0].s3_canonical_user_id
    }
    Action   = "s3:GetObject"
    Resource = "${var.s3_bucket_arn}/*"
  }) : null
}

output "origin_access_type" {
  description = "The type of origin access being used (oai or oac)"
  value       = var.origin_access_type
}

# -----------------------------------------------------------------------------
# Secondary OAC Outputs (for multi-origin distributions)
# -----------------------------------------------------------------------------

output "secondary_oac_id" {
  description = "ID of the secondary Origin Access Control (null if not using secondary origin)"
  value       = length(aws_cloudfront_origin_access_control.secondary) > 0 ? aws_cloudfront_origin_access_control.secondary[0].id : null
}

output "secondary_oac_etag" {
  description = "ETag of the secondary Origin Access Control (null if not using secondary origin)"
  value       = length(aws_cloudfront_origin_access_control.secondary) > 0 ? aws_cloudfront_origin_access_control.secondary[0].etag : null
}
