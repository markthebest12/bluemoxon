# =============================================================================
# Infrastructure Outputs
# =============================================================================

# =============================================================================
# Environment Info
# =============================================================================

output "environment" {
  description = "Current environment"
  value       = var.environment
}

output "aws_account_id" {
  description = "AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "AWS region"
  value       = data.aws_region.current.name
}

# =============================================================================
# S3 Buckets
# =============================================================================

output "frontend_bucket_name" {
  description = "Frontend S3 bucket name"
  value       = module.frontend_bucket.bucket_name
}

output "images_bucket_name" {
  description = "Images S3 bucket name"
  value       = module.images_bucket.bucket_name
}

# =============================================================================
# CloudFront
# =============================================================================

output "frontend_cdn_domain" {
  description = "Frontend CloudFront domain"
  value       = var.enable_cloudfront ? module.frontend_cdn[0].distribution_domain_name : null
}

output "frontend_cdn_distribution_id" {
  description = "Frontend CloudFront distribution ID"
  value       = var.enable_cloudfront ? module.frontend_cdn[0].distribution_id : null
}

output "images_cdn_domain" {
  description = "Images CloudFront domain"
  value       = var.enable_cloudfront ? module.images_cdn[0].distribution_domain_name : null
}

output "images_cdn_distribution_id" {
  description = "Images CloudFront distribution ID"
  value       = var.enable_cloudfront ? module.images_cdn[0].distribution_id : null
}

# =============================================================================
# Cognito
# =============================================================================

output "cognito_user_pool_id" {
  description = "Cognito user pool ID"
  value       = module.cognito.user_pool_id
}

output "cognito_client_id" {
  description = "Cognito app client ID"
  value       = module.cognito.client_id
}

output "cognito_domain" {
  description = "Cognito domain"
  value       = module.cognito.domain
}

# =============================================================================
# Domains
# =============================================================================

output "api_domain" {
  description = "API domain name"
  value       = local.api_domain
}

output "app_domain" {
  description = "App domain name"
  value       = local.app_domain
}
