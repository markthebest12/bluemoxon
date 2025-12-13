output "api_domain" {
  description = "API domain name"
  value       = local.api_domain
}

output "app_domain" {
  description = "App domain name"
  value       = local.app_domain
}

output "aws_account_id" {
  description = "AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "AWS region"
  value       = data.aws_region.current.name
}

output "cognito_client_id" {
  description = "Cognito app client ID"
  value       = var.enable_cognito ? module.cognito[0].client_id : null
}

output "cognito_domain" {
  description = "Cognito domain"
  value       = var.enable_cognito ? module.cognito[0].domain : null
}

output "cognito_user_pool_id" {
  description = "Cognito user pool ID"
  value       = var.enable_cognito ? module.cognito[0].user_pool_id : null
}

output "environment" {
  description = "Current environment"
  value       = var.environment
}

output "frontend_bucket_name" {
  description = "Frontend S3 bucket name"
  value       = module.frontend_bucket.bucket_name
}

output "frontend_cdn_distribution_id" {
  description = "Frontend CloudFront distribution ID"
  value       = var.enable_cloudfront ? module.frontend_cdn[0].distribution_id : null
}

output "frontend_cdn_domain" {
  description = "Frontend CloudFront domain"
  value       = var.enable_cloudfront ? module.frontend_cdn[0].distribution_domain_name : null
}

output "images_bucket_name" {
  description = "Images S3 bucket name"
  value       = module.images_bucket.bucket_name
}

output "images_cdn_distribution_id" {
  description = "Images CloudFront distribution ID"
  value       = var.enable_cloudfront ? module.images_cdn[0].distribution_id : null
}

output "images_cdn_domain" {
  description = "Images CloudFront domain"
  value       = var.enable_cloudfront ? module.images_cdn[0].distribution_domain_name : null
}

# =============================================================================
# Lambda Outputs
# =============================================================================

output "lambda_function_name" {
  description = "Lambda function name"
  value       = var.enable_lambda ? module.lambda[0].function_name : var.lambda_function_name_external
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = var.enable_lambda ? module.lambda[0].function_arn : null
}

output "lambda_invoke_arn" {
  description = "Lambda invoke ARN"
  value       = var.enable_lambda ? module.lambda[0].invoke_arn : var.lambda_invoke_arn_external
}

# =============================================================================
# API Gateway Outputs
# =============================================================================

output "api_gateway_endpoint" {
  description = "API Gateway endpoint URL"
  value       = module.api_gateway.api_endpoint
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = module.api_gateway.api_id
}

# =============================================================================
# Database Outputs (when enabled)
# =============================================================================

output "database_endpoint" {
  description = "RDS database endpoint"
  value       = var.enable_database ? module.database[0].endpoint : null
}

output "database_secret_arn" {
  description = "Database credentials secret ARN"
  value       = var.enable_database ? module.database_secret[0].arn : null
}

output "db_sync_lambda_name" {
  description = "Database sync Lambda function name"
  value       = var.enable_database && var.environment == "staging" ? module.db_sync_lambda[0].function_name : null
}

output "analysis_worker_function_name" {
  description = "Analysis worker Lambda function name"
  value       = local.analysis_worker_enabled ? module.analysis_worker[0].function_name : null
}

output "analysis_queue_url" {
  description = "SQS queue URL for analysis jobs"
  value       = local.analysis_worker_enabled ? module.analysis_worker[0].queue_url : null
}

output "analysis_dlq_url" {
  description = "SQS dead letter queue URL for failed analysis jobs"
  value       = local.analysis_worker_enabled ? module.analysis_worker[0].dlq_url : null
}

# =============================================================================
# GitHub OIDC Outputs
# =============================================================================

output "github_oidc_role_arn" {
  description = "GitHub Actions IAM role ARN"
  value       = var.enable_github_oidc ? module.github_oidc[0].role_arn : null
}

output "github_oidc_provider_arn" {
  description = "GitHub OIDC provider ARN"
  value       = var.enable_github_oidc ? module.github_oidc[0].oidc_provider_arn : null
}
