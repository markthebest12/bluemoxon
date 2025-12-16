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

  # Lambda VPC enabled - defaults to enable_database if not explicitly set
  # Allows prod to have Lambda in VPC without managing RDS via Terraform
  enable_lambda_vpc = coalesce(var.enable_lambda_vpc, var.enable_database)

  # VPC ID for Lambda - use override if provided (prod has dedicated VPC)
  # Default: uses data.aws_vpc.default[0].id
  # Prod override: vpc-023f4b1dc7c2c4296 (bluemoxon-vpc)
  lambda_vpc_id = local.enable_lambda_vpc ? coalesce(var.prod_vpc_id, try(data.aws_vpc.default[0].id, null)) : null

  # Analysis worker enabled - defaults to enable_lambda if not explicitly set
  # Allows enabling analysis worker when main Lambda is managed externally
  analysis_worker_enabled = coalesce(var.enable_analysis_worker, var.enable_lambda)

  # Eval runbook worker enabled - defaults to enable_lambda if not explicitly set
  # Allows enabling eval runbook worker when main Lambda is managed externally
  eval_runbook_worker_enabled = coalesce(var.enable_eval_runbook_worker, var.enable_lambda)

  # Scraper Lambda enabled - defaults to enable_lambda if not explicitly set
  # Allows disabling scraper when using existing scraper (prod uses bluemoxon-production-scraper)
  scraper_enabled = coalesce(var.enable_scraper, var.enable_lambda)

  # Scraper Lambda ARN - uses module output when Terraform-managed, otherwise variable
  # This resolves to the correct ARN whether scraper is created by module or exists externally
  scraper_lambda_arn = local.scraper_enabled ? (
    try(module.scraper_lambda[0].function_arn, null)
  ) : var.scraper_lambda_arn

  # Lambda role name for SQS permissions
  # Uses override when provided (required for import workflow), falls back to module output
  # For external Lambda, uses external_lambda_role_name
  api_lambda_role_name = var.enable_lambda ? (
    coalesce(var.lambda_iam_role_name_override, try(module.lambda[0].role_name, null))
  ) : var.external_lambda_role_name

  # Security group for worker VPC config
  # Uses external SG when provided (required for import workflow), falls back to module output
  lambda_security_group_id = var.enable_lambda ? (
    coalesce(var.external_lambda_security_group_id, try(module.lambda[0].security_group_id, null))
  ) : var.external_lambda_security_group_id
}
