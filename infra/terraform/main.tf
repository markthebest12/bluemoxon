# =============================================================================
# BlueMoxon Infrastructure
# =============================================================================
# This configuration deploys the BlueMoxon application infrastructure.
# Use environment-specific tfvars files to switch between staging and prod:
#
#   terraform init -backend-config="key=bluemoxon/staging/terraform.tfstate"
#   terraform plan -var-file=envs/staging.tfvars
#   terraform apply -var-file=envs/staging.tfvars
#
# =============================================================================

# =============================================================================
# Data Sources
# =============================================================================

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# =============================================================================
# S3 Buckets
# =============================================================================

module "frontend_bucket" {
  source = "./modules/s3"

  bucket_name              = local.frontend_bucket_name
  enable_versioning        = false
  block_public_access      = true
  enable_website           = false
  enable_cloudfront_policy = var.enable_cloudfront
  cloudfront_oai_arn       = var.enable_cloudfront ? module.frontend_cdn[0].oai_arn : null

  tags = local.common_tags
}

module "images_bucket" {
  source = "./modules/s3"

  bucket_name              = local.images_bucket_name
  enable_versioning        = true
  block_public_access      = true
  enable_cloudfront_policy = var.enable_cloudfront
  cloudfront_oai_arn       = var.enable_cloudfront ? module.images_cdn[0].oai_arn : null

  cors_allowed_origins = [
    "https://${local.app_domain}",
    "https://${local.api_domain}"
  ]
  cors_allowed_methods = ["GET", "HEAD"]

  tags = local.common_tags
}

# =============================================================================
# CloudFront Distributions (optional)
# =============================================================================

module "frontend_cdn" {
  count  = var.enable_cloudfront ? 1 : 0
  source = "./modules/cloudfront"

  s3_bucket_name        = module.frontend_bucket.bucket_name
  s3_bucket_domain_name = module.frontend_bucket.bucket_regional_domain_name
  domain_aliases        = [] # Add custom domain when ACM cert is ready
  acm_certificate_arn   = null
  oai_comment           = "OAI for ${local.frontend_bucket_name}"
  comment               = "BlueMoxon Frontend - ${var.environment}"

  tags = local.common_tags
}

module "images_cdn" {
  count  = var.enable_cloudfront ? 1 : 0
  source = "./modules/cloudfront"

  s3_bucket_name        = module.images_bucket.bucket_name
  s3_bucket_domain_name = module.images_bucket.bucket_regional_domain_name
  domain_aliases        = []
  acm_certificate_arn   = null
  default_root_object   = ""
  oai_comment           = "OAI for ${local.images_bucket_name}"
  comment               = "BlueMoxon Images CDN - ${var.environment}"
  default_ttl           = 604800  # 7 days for images
  max_ttl               = 2592000 # 30 days

  tags = local.common_tags
}

# =============================================================================
# Cognito User Pool
# =============================================================================

module "cognito" {
  source = "./modules/cognito"

  user_pool_name = "${var.app_name}-users-${var.environment}"
  domain_prefix  = "${var.app_name}-${var.environment}"

  callback_urls = [
    "https://${local.app_domain}/auth/callback",
    "http://localhost:5173/auth/callback"
  ]
  logout_urls = [
    "https://${local.app_domain}",
    "http://localhost:5173"
  ]

  enable_oauth = true

  tags = local.common_tags
}

# =============================================================================
# Lambda Function
# =============================================================================

module "api_lambda" {
  source = "./modules/lambda"

  environment   = var.environment
  function_name = local.lambda_function_name
  handler       = "app.main.handler"
  runtime       = var.lambda_runtime
  memory_size   = var.lambda_memory_size
  timeout       = var.lambda_timeout

  # Use placeholder for initial creation - CI/CD updates the code
  package_path     = "${path.module}/placeholder/placeholder.zip"
  source_code_hash = filebase64sha256("${path.module}/placeholder/placeholder.zip")

  provisioned_concurrency = var.lambda_provisioned_concurrency

  environment_variables = {
    DATABASE_URL         = "" # Set via SSM or Secrets Manager in production
    COGNITO_USER_POOL_ID = module.cognito.user_pool_id
    COGNITO_CLIENT_ID    = module.cognito.client_id
    IMAGES_BUCKET        = module.images_bucket.bucket_name
    IMAGES_CDN_DOMAIN    = var.enable_cloudfront ? module.images_cdn[0].distribution_domain_name : ""
    FRONTEND_URL         = "https://${local.app_domain}"
    CORS_ORIGINS         = "https://${local.app_domain}"
  }

  tags = local.common_tags
}

# =============================================================================
# API Gateway
# =============================================================================

module "api_gateway" {
  source = "./modules/api-gateway"

  api_name             = local.api_gateway_name
  lambda_invoke_arn    = module.api_lambda.invoke_arn
  lambda_function_name = module.api_lambda.function_name

  cors_allowed_origins = [
    "https://${local.app_domain}",
    "http://localhost:5173"
  ]
  cors_allowed_headers = ["*"]
  cors_allowed_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
  cors_expose_headers  = ["x-app-version", "x-environment"]

  tags = local.common_tags
}

# =============================================================================
# Outputs Reference
# =============================================================================
# See outputs.tf for all exported values
