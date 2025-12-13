# =============================================================================
# Local Values
# =============================================================================

locals {
  # Resource naming convention: {app}-{environment}-{resource}
  # Aligns with existing staging resources: bluemoxon-staging-api, bluemoxon-staging-frontend
  name_prefix = "${var.app_name}-${var.environment}"

  # Common tags applied to all resources
  common_tags = {
    Application = var.app_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  # S3 bucket names - use override if provided (for legacy prod naming)
  # Default: bluemoxon-frontend-staging, bluemoxon-images-staging
  # Prod override: bluemoxon-frontend, bluemoxon-images
  frontend_bucket_name = coalesce(var.frontend_bucket_name_override, "${var.app_name}-frontend-${var.environment}")
  images_bucket_name   = coalesce(var.images_bucket_name_override, "${var.app_name}-images-${var.environment}")

  # Lambda function name - use override if provided (for legacy prod naming)
  # Default: bluemoxon-staging-api
  # Prod override: bluemoxon-api
  lambda_function_name = coalesce(var.lambda_function_name_override, "${var.app_name}-${var.environment}-api")

  # API Gateway name - use override if provided
  api_gateway_name = coalesce(var.api_gateway_name_override, "${var.app_name}-${var.environment}-api")

  # Cognito user pool name - use override if provided (for legacy prod naming)
  # Default: bluemoxon-users-staging
  # Prod override: bluemoxon-users
  cognito_user_pool_name = coalesce(var.cognito_user_pool_name_override, "${var.app_name}-users-${var.environment}")

  # Cognito domain prefix - use override if provided
  # Default: bluemoxon-staging
  # Prod override: bluemoxon
  cognito_domain = coalesce(var.cognito_domain_override, "${var.app_name}-${var.environment}")

  # Domain configuration
  api_domain = "${var.api_subdomain}.${var.domain_name}"
  app_domain = "${var.app_subdomain}.${var.domain_name}"

  # Environment-specific settings
  is_prod = var.environment == "prod"

  # Analysis worker enabled - defaults to enable_lambda if not explicitly set
  # Allows enabling analysis worker when main Lambda is managed externally
  analysis_worker_enabled = coalesce(var.enable_analysis_worker, var.enable_lambda)

  # Lambda role name for SQS permissions - use external if Lambda disabled
  api_lambda_role_name = var.enable_lambda ? (
    length(module.lambda) > 0 ? module.lambda[0].role_name : null
  ) : var.external_lambda_role_name

  # Security group for worker VPC config - use external if Lambda disabled
  lambda_security_group_id = var.enable_lambda ? (
    length(module.lambda) > 0 ? module.lambda[0].security_group_id : null
  ) : var.external_lambda_security_group_id
}
