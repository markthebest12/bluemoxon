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
  value       = var.enable_cognito ? module.cognito[0].client_id : var.cognito_client_id_external

  precondition {
    condition     = var.enable_cognito || (var.cognito_client_id_external != null && var.cognito_client_id_external != "")
    error_message = "cognito_client_id_external must be set when enable_cognito is false"
  }
}

output "cognito_domain" {
  description = "Cognito domain (full auth domain)"
  value = var.enable_cognito ? (
    module.cognito[0].domain != null ? "${module.cognito[0].domain}.auth.${data.aws_region.current.name}.amazoncognito.com" : null
    ) : (
    var.cognito_domain_override != null ? "${var.cognito_domain_override}.auth.${data.aws_region.current.name}.amazoncognito.com" : null
  )

  precondition {
    condition     = var.enable_cognito || (var.cognito_domain_override != null && var.cognito_domain_override != "")
    error_message = "cognito_domain_override must be set when enable_cognito is false"
  }
}

output "cognito_user_pool_id" {
  description = "Cognito user pool ID"
  value       = var.enable_cognito ? module.cognito[0].user_pool_id : var.cognito_user_pool_id_external

  precondition {
    condition     = var.enable_cognito || (var.cognito_user_pool_id_external != null && var.cognito_user_pool_id_external != "")
    error_message = "cognito_user_pool_id_external must be set when enable_cognito is false"
  }
}

output "environment" {
  description = "Current environment"
  value       = var.environment
}

output "frontend_bucket_name" {
  description = "Frontend S3 bucket name"
  value       = module.frontend_bucket.bucket_name
}

output "artifacts_bucket_name" {
  description = "S3 bucket for CI/CD artifacts (Lambda packages, layers)"
  value       = module.artifacts_bucket.bucket_name
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

  precondition {
    condition     = var.enable_lambda || (var.lambda_function_name_external != null && var.lambda_function_name_external != "")
    error_message = "lambda_function_name_external must be set when enable_lambda is false"
  }
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = var.enable_lambda ? module.lambda[0].function_arn : null
}

output "lambda_invoke_arn" {
  description = "Lambda invoke ARN"
  value       = var.enable_lambda ? module.lambda[0].invoke_arn : var.lambda_invoke_arn_external

  precondition {
    condition     = var.enable_lambda || (var.lambda_invoke_arn_external != null && var.lambda_invoke_arn_external != "")
    error_message = "lambda_invoke_arn_external must be set when enable_lambda is false"
  }
}

# =============================================================================
# Lambda Layer Outputs
# =============================================================================

output "lambda_layer_arn" {
  description = "Lambda layer ARN (without version)"
  value       = var.enable_lambda ? module.lambda_layer[0].layer_arn : null
}

output "lambda_layer_version_arn" {
  description = "Lambda layer version ARN (with version)"
  value       = var.enable_lambda ? module.lambda_layer[0].layer_version_arn : null
}

output "lambda_layer_version" {
  description = "Lambda layer version number"
  value       = var.enable_lambda ? module.lambda_layer[0].layer_version : null
}

# =============================================================================
# API Gateway Outputs (when enabled)
# =============================================================================

output "api_gateway_endpoint" {
  description = "API Gateway endpoint URL"
  value       = var.enable_api_gateway ? module.api_gateway[0].api_endpoint : null
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = var.enable_api_gateway ? module.api_gateway[0].api_id : null
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

output "eval_runbook_worker_function_name" {
  description = "Eval runbook worker Lambda function name"
  value       = local.eval_runbook_worker_enabled ? module.eval_runbook_worker[0].function_name : null
}

output "eval_runbook_queue_url" {
  description = "SQS queue URL for eval runbook jobs"
  value       = local.eval_runbook_worker_enabled ? module.eval_runbook_worker[0].queue_url : null
}

output "eval_runbook_dlq_url" {
  description = "SQS dead letter queue URL for failed eval runbook jobs"
  value       = local.eval_runbook_worker_enabled ? module.eval_runbook_worker[0].dlq_url : null
}

# =============================================================================
# Tracking Worker Outputs
# =============================================================================

output "tracking_dispatcher_function_name" {
  description = "Tracking dispatcher Lambda function name"
  value       = local.tracking_worker_enabled ? module.tracking_worker[0].dispatcher_function_name : null
}

output "tracking_worker_function_name" {
  description = "Tracking worker Lambda function name"
  value       = local.tracking_worker_enabled ? module.tracking_worker[0].worker_function_name : null
}

output "tracking_queue_url" {
  description = "Tracking jobs SQS queue URL"
  value       = local.tracking_worker_enabled ? module.tracking_worker[0].queue_url : null
}

# =============================================================================
# Cleanup Lambda Outputs
# =============================================================================

output "cleanup_lambda_function_name" {
  description = "Cleanup Lambda function name"
  value       = local.cleanup_lambda_enabled ? module.cleanup_lambda[0].function_name : null
}

output "cleanup_lambda_function_arn" {
  description = "Cleanup Lambda function ARN"
  value       = local.cleanup_lambda_enabled ? module.cleanup_lambda[0].function_arn : null
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

# =============================================================================
# Scraper Outputs (when enabled)
# =============================================================================

output "scraper_function_name" {
  description = "Scraper Lambda function name"
  value       = local.scraper_enabled ? module.scraper_lambda[0].function_name : null
}

output "scraper_function_arn" {
  description = "Scraper Lambda function ARN"
  value       = local.scraper_enabled ? module.scraper_lambda[0].function_arn : null
}

output "scraper_ecr_repository" {
  description = "Scraper ECR repository name (without registry URL prefix)"
  value       = local.scraper_enabled ? module.scraper_lambda[0].ecr_repository_name : null
}

output "scraper_ecr_repository_url" {
  description = "Scraper ECR repository full URL"
  value       = local.scraper_enabled ? module.scraper_lambda[0].ecr_repository_url : null
}

# =============================================================================
# Full URLs (for deploy workflow)
# =============================================================================

output "api_url" {
  description = "Full API URL with path prefix"
  value       = "https://${local.api_domain}/api/v1"
}

output "app_url" {
  description = "Full app URL"
  value       = "https://${local.app_domain}"
}

# =============================================================================
# ElastiCache Outputs (#1002 Dashboard Caching)
# =============================================================================

output "redis_url" {
  description = "Redis URL for Lambda environment variable"
  value       = var.enable_elasticache ? module.elasticache[0].redis_endpoint : ""
  sensitive   = true
}

# =============================================================================
# Image Processor Outputs
# =============================================================================

output "image_processor_function_name" {
  description = "Image processor Lambda function name"
  value       = local.image_processor_enabled ? module.image_processor[0].function_name : null
}

output "image_processor_ecr_url" {
  description = "Image processor ECR repository URL"
  value       = aws_ecr_repository.image_processor.repository_url
}

# =============================================================================
# Alerts Outputs
# =============================================================================

output "alerts_sns_topic_arn" {
  description = "SNS topic ARN for CloudWatch alarms and operational alerts"
  value       = aws_sns_topic.alerts.arn
}

# =============================================================================
# Pre-flight Validation Outputs
# =============================================================================

output "lambda_environment_variables" {
  description = "Environment variables configured for the API Lambda (for pre-flight validation)"
  value       = var.enable_lambda ? module.lambda[0].environment_variables : {}
  sensitive   = true # May contain API keys
}
