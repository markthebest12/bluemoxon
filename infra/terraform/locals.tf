# =============================================================================
# Local Values
# =============================================================================

locals {
  # Resource naming convention: {app}-{resource}-{environment}
  name_prefix = "${var.app_name}-${var.environment}"

  # Common tags applied to all resources
  common_tags = {
    Application = var.app_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  # S3 bucket names
  frontend_bucket_name = "${var.app_name}-frontend-${var.environment}"
  images_bucket_name   = "${var.app_name}-images-${var.environment}"

  # Lambda function name (format: {app}-{environment}-{resource} to match deploy workflow)
  lambda_function_name = "${var.app_name}-${var.environment}-api"

  # API Gateway name
  api_gateway_name = "${var.app_name}-${var.environment}-api"

  # Domain configuration
  api_domain = "${var.api_subdomain}.${var.domain_name}"
  app_domain = "${var.app_subdomain}.${var.domain_name}"

  # Environment-specific settings
  is_prod = var.environment == "prod"
}
