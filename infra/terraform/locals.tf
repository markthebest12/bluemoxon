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

  # S3 bucket names - match existing bucket naming convention
  # Existing buckets: bluemoxon-frontend-staging, bluemoxon-images-staging
  frontend_bucket_name = "${var.app_name}-frontend-${var.environment}"
  images_bucket_name   = "${var.app_name}-images-${var.environment}"

  # Lambda function name - match existing workflow naming convention
  lambda_function_name = "${var.app_name}-${var.environment}-api"

  # API Gateway name
  api_gateway_name = "${var.app_name}-${var.environment}-api"

  # Domain configuration
  api_domain = "${var.api_subdomain}.${var.domain_name}"
  app_domain = "${var.app_subdomain}.${var.domain_name}"

  # Environment-specific settings
  is_prod = var.environment == "prod"
}
