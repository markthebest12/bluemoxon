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

# Default VPC and subnets (for RDS and Lambda VPC access)
data "aws_vpc" "default" {
  count   = var.enable_database ? 1 : 0
  default = true
}

data "aws_subnets" "default" {
  count = var.enable_database ? 1 : 0
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default[0].id]
  }
}

# =============================================================================
# S3 Buckets
# =============================================================================

module "frontend_bucket" {
  source = "./modules/s3"

  bucket_name              = local.frontend_bucket_name
  enable_versioning        = true # DR: enables recovery of deleted/overwritten objects
  block_public_access      = true
  enable_website           = false
  enable_cloudfront_policy = var.enable_cloudfront && !var.skip_s3_cloudfront_policy
  cloudfront_oai_arn       = var.enable_cloudfront && !var.skip_s3_cloudfront_policy ? module.frontend_cdn[0].oai_arn : null

  tags = local.common_tags
}

module "images_bucket" {
  source = "./modules/s3"

  bucket_name              = local.images_bucket_name
  enable_versioning        = true
  block_public_access      = true
  enable_cloudfront_policy = var.enable_cloudfront && !var.skip_s3_cloudfront_policy
  cloudfront_oai_arn       = var.enable_cloudfront && !var.skip_s3_cloudfront_policy ? module.images_cdn[0].oai_arn : null

  cors_allowed_origins = [
    "https://${local.app_domain}",
    "https://${local.api_domain}"
  ]
  cors_allowed_methods = ["GET", "HEAD"]

  tags = local.common_tags
}

module "logs_bucket" {
  count  = var.logs_bucket_name != null ? 1 : 0
  source = "./modules/s3"

  bucket_name         = var.logs_bucket_name
  enable_versioning   = false
  block_public_access = false # Required for CloudFront log delivery ACL grants

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
  domain_aliases        = var.frontend_acm_cert_arn != null ? [local.app_domain] : []
  acm_certificate_arn   = var.frontend_acm_cert_arn
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

  user_pool_name                 = local.cognito_user_pool_name
  user_pool_client_name_override = var.cognito_client_name_override
  domain_prefix                  = local.cognito_domain

  callback_urls = var.cognito_callback_urls_override != null ? var.cognito_callback_urls_override : [
    "https://${local.app_domain}/auth/callback",
    "http://localhost:5173/auth/callback"
  ]
  logout_urls = var.cognito_logout_urls_override != null ? var.cognito_logout_urls_override : [
    "https://${local.app_domain}",
    "http://localhost:5173"
  ]

  enable_oauth = true

  # MFA configuration
  mfa_configuration        = var.cognito_mfa_configuration
  mfa_totp_enabled         = var.cognito_mfa_totp_enabled
  password_require_symbols = var.cognito_password_require_symbols

  # Admin create user config
  allow_admin_create_user_only = var.cognito_allow_admin_create_user_only
  invite_email_message         = var.cognito_invite_email_message
  invite_email_subject         = var.cognito_invite_email_subject

  tags = local.common_tags
}

# =============================================================================
# VPC Networking (NAT Gateway for Lambda outbound access)
# =============================================================================

module "vpc_networking" {
  count  = var.enable_nat_gateway ? 1 : 0
  source = "./modules/vpc-networking"

  vpc_id             = data.aws_vpc.default[0].id
  name_prefix        = local.name_prefix
  enable_nat_gateway = true
  public_subnet_id   = var.public_subnet_id
  private_subnet_ids = var.private_subnet_ids

  # VPC Endpoints for Lambda to access AWS services
  enable_vpc_endpoints        = var.enable_database
  create_lambda_sg_rule       = false # Will be enabled after initial import
  lambda_security_group_id    = var.enable_database && var.enable_lambda ? module.lambda[0].security_group_id : null
  cognito_endpoint_subnet_ids = var.cognito_endpoint_subnet_ids
  # Disable Cognito VPC endpoint - ManagedLogin doesn't support PrivateLink
  # Lambda uses NAT gateway to reach Cognito API instead
  enable_cognito_endpoint = false

  tags = local.common_tags
}

# =============================================================================
# Database (RDS PostgreSQL)
# =============================================================================

module "database_secret" {
  count  = var.enable_database ? 1 : 0
  source = "./modules/secrets"

  secret_name = "${local.name_prefix}/database"
  description = "Database credentials for ${local.name_prefix}"

  secret_value = {
    username = var.db_username
    password = var.db_password
    host     = module.database[0].address
    port     = tostring(module.database[0].port)
    database = var.db_name
  }

  tags = local.common_tags

  depends_on = [module.database]
}

module "database" {
  count  = var.enable_database ? 1 : 0
  source = "./modules/rds"

  identifier    = "${local.name_prefix}-db"
  database_name = var.db_name

  master_username = var.db_username
  master_password = var.db_password

  instance_class    = var.db_instance_class
  allocated_storage = var.db_allocated_storage

  vpc_id     = data.aws_vpc.default[0].id
  subnet_ids = data.aws_subnets.default[0].ids

  # Allow Lambda security group to access RDS
  allowed_security_group_id = var.enable_lambda ? module.lambda[0].security_group_id : null

  # Staging-specific settings
  deletion_protection     = local.is_prod
  skip_final_snapshot     = !local.is_prod
  backup_retention_period = local.is_prod ? 7 : 1

  tags = local.common_tags
}

# =============================================================================
# Lambda Function
# =============================================================================

module "lambda" {
  count  = var.enable_lambda ? 1 : 0
  source = "./modules/lambda"

  function_name    = local.lambda_function_name
  environment      = var.environment
  package_path     = var.lambda_package_path
  source_code_hash = var.lambda_source_code_hash

  runtime     = var.lambda_runtime
  memory_size = var.lambda_memory_size
  timeout     = var.lambda_timeout

  provisioned_concurrency = var.lambda_provisioned_concurrency

  # VPC configuration (when database is enabled)
  # Use private_subnet_ids if NAT gateway is enabled, otherwise use all default subnets
  create_security_group = var.enable_database
  vpc_id                = var.enable_database ? data.aws_vpc.default[0].id : null
  subnet_ids            = var.enable_database ? (var.enable_nat_gateway ? var.private_subnet_ids : data.aws_subnets.default[0].ids) : []

  # Secrets Manager access (use ARN pattern to avoid circular dependency)
  secrets_arns = var.enable_database ? [
    "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}/database*"
  ] : []

  # S3 bucket access
  s3_bucket_arns = [module.images_bucket.bucket_arn]

  # Cognito access for user management
  cognito_user_pool_arns = [module.cognito.user_pool_arn]

  # Bedrock model access for AI-powered analysis generation
  bedrock_model_ids = [
    "anthropic.claude-sonnet-4-5-20240929",
    "anthropic.claude-opus-4-5-20251101"
  ]

  # Environment variables (secret ARN set after database_secret is created)
  environment_variables = merge(
    {
      CORS_ORIGINS          = "https://${local.app_domain},http://localhost:5173"
      IMAGES_CDN_DOMAIN     = var.enable_cloudfront ? module.images_cdn[0].distribution_domain_name : ""
      COGNITO_USER_POOL_ID  = module.cognito.user_pool_id
      COGNITO_APP_CLIENT_ID = module.cognito.client_id
      IMAGES_BUCKET         = module.images_bucket.bucket_name
      API_KEY_HASH          = var.api_key_hash
      ALLOWED_EDITOR_EMAILS = var.allowed_editor_emails
      MAINTENANCE_MODE      = var.maintenance_mode
      # Analysis worker queue name (URL constructed at runtime)
      ANALYSIS_QUEUE_NAME = "${local.name_prefix}-analysis-jobs"
    },
    var.enable_database ? {
      DATABASE_SECRET_NAME = "${local.name_prefix}/database"
    } : {}
  )

  tags = local.common_tags
}

# =============================================================================
# Database Sync Lambda (staging only)
# =============================================================================

module "db_sync_lambda" {
  count  = var.enable_database && var.enable_lambda && !local.is_prod ? 1 : 0
  source = "./modules/db-sync-lambda"

  function_name = "${local.name_prefix}-db-sync"

  # Use private subnets (with NAT gateway route) for outbound internet access
  subnet_ids         = var.enable_nat_gateway ? var.private_subnet_ids : data.aws_subnets.default[0].ids
  security_group_ids = [module.lambda[0].security_group_id]

  # Access to both prod and staging secrets
  secret_arns = [
    # Staging secret
    "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}/database*",
    # Production secret (cross-account, requires resource policy on prod secret)
    var.prod_database_secret_arn
  ]

  # Cognito pool for user mapping after DB sync
  cognito_user_pool_id = module.cognito.user_pool_id

  environment_variables = {
    PROD_SECRET_ARN      = var.prod_database_secret_arn
    STAGING_SECRET_ARN   = module.database_secret[0].arn
    PROD_SECRET_REGION   = "us-west-2"
    COGNITO_USER_POOL_ID = module.cognito.user_pool_id
  }

  tags = local.common_tags

  depends_on = [module.database_secret]
}

# =============================================================================
# Scraper Lambda (Playwright-based eBay scraping)
# =============================================================================

module "scraper_lambda" {
  count  = var.enable_lambda ? 1 : 0
  source = "./modules/scraper-lambda"

  name_prefix = local.name_prefix
  environment = var.environment

  # Allow API Lambda to invoke scraper
  api_lambda_role_name = module.lambda[0].role_name
  api_lambda_role_arn  = module.lambda[0].role_arn

  # S3 bucket for scraped images
  images_bucket_arn  = module.images_bucket.bucket_arn
  images_bucket_name = module.images_bucket.bucket_name

  # Scraper settings
  image_tag   = "v1.0.7"
  memory_size = 1024 # Playwright needs significant memory
  timeout     = 90   # Allow more time for S3 uploads (24 images)

  environment_variables = {
    ENVIRONMENT = var.environment
  }

  tags = local.common_tags
}

# =============================================================================
# Analysis Worker (async Bedrock analysis with SQS)
# =============================================================================

module "analysis_worker" {
  count  = var.enable_lambda ? 1 : 0
  source = "./modules/analysis-worker"

  name_prefix = local.name_prefix
  environment = var.environment

  package_path     = var.lambda_package_path
  source_code_hash = var.lambda_source_code_hash
  runtime          = var.lambda_runtime

  # Match API Lambda timeout + buffer for SQS visibility
  timeout              = 600
  visibility_timeout   = 660
  memory_size          = 256
  reserved_concurrency = 5

  # VPC configuration (same as API Lambda)
  subnet_ids         = var.enable_database ? (var.enable_nat_gateway ? var.private_subnet_ids : data.aws_subnets.default[0].ids) : []
  security_group_ids = var.enable_database ? [module.lambda[0].security_group_id] : []

  # Secrets Manager access
  secrets_arns = var.enable_database ? [
    "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}/database*"
  ] : []

  # S3 bucket access
  s3_bucket_arns = [module.images_bucket.bucket_arn]

  # Bedrock model access
  bedrock_model_ids = [
    "anthropic.claude-sonnet-4-5-20240929",
    "anthropic.claude-opus-4-5-20251101"
  ]

  # Allow API Lambda to send messages to SQS
  api_lambda_role_name = module.lambda[0].role_name

  # Environment variables
  environment_variables = merge(
    {
      IMAGES_CDN_DOMAIN = var.enable_cloudfront ? module.images_cdn[0].distribution_domain_name : ""
      IMAGES_BUCKET     = module.images_bucket.bucket_name
    },
    var.enable_database ? {
      DATABASE_SECRET_NAME = "${local.name_prefix}/database"
    } : {}
  )

  tags = local.common_tags
}

# =============================================================================
# API Gateway
# =============================================================================

module "api_gateway" {
  source = "./modules/api-gateway"

  api_name = local.api_gateway_name

  # Use Lambda module outputs when enabled, otherwise use external values
  lambda_function_name = var.enable_lambda ? module.lambda[0].function_name : var.lambda_function_name_external
  lambda_invoke_arn    = var.enable_lambda ? module.lambda[0].invoke_arn : var.lambda_invoke_arn_external

  cors_allowed_origins = [
    "https://${local.app_domain}",
    "http://localhost:5173"
  ]

  # Custom domain (optional)
  domain_name     = var.api_acm_cert_arn != null ? local.api_domain : null
  certificate_arn = var.api_acm_cert_arn

  tags = local.common_tags
}

# =============================================================================
# Landing Site (marketing site at bluemoxon.com)
# =============================================================================

module "landing_site" {
  count  = var.enable_landing_site ? 1 : 0
  source = "./modules/landing-site"

  bucket_name     = var.landing_bucket_name
  oac_name        = "${var.landing_bucket_name}-oac"
  oac_description = "OAC for BlueMoxon landing site"
  origin_id       = "${var.landing_bucket_name}-s3"
  comment         = "BlueMoxon Landing/Docs Site"
  domain_aliases  = ["${var.domain_name}", "www.${var.domain_name}"]

  acm_certificate_arn = var.landing_acm_cert_arn

  tags = local.common_tags
}

# =============================================================================
# GitHub Actions OIDC (for CI/CD deployments)
# =============================================================================

module "github_oidc" {
  count  = var.enable_github_oidc ? 1 : 0
  source = "./modules/github-oidc"

  github_repo = var.github_repo

  # Lambda deployment permissions - use wildcard pattern for all app functions
  lambda_function_arns = [
    "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:${var.app_name}-*"
  ]

  # S3 bucket permissions - use overrides if provided, otherwise use terraform module outputs
  frontend_bucket_arns = length(var.github_oidc_frontend_bucket_arns) > 0 ? var.github_oidc_frontend_bucket_arns : [
    module.frontend_bucket.bucket_arn
  ]

  images_bucket_arns = length(var.github_oidc_images_bucket_arns) > 0 ? var.github_oidc_images_bucket_arns : [
    module.images_bucket.bucket_arn
  ]

  # CloudFront permissions - use overrides if provided, otherwise use terraform module outputs
  cloudfront_distribution_arns = length(var.github_oidc_cloudfront_distribution_arns) > 0 ? var.github_oidc_cloudfront_distribution_arns : (
    var.enable_cloudfront ? [module.frontend_cdn[0].distribution_arn] : []
  )

  tags = local.common_tags
}

# =============================================================================
# DNS (Route53 hosted zone and records - prod only)
# =============================================================================

module "dns" {
  count  = var.enable_dns ? 1 : 0
  source = "./modules/dns"

  domain_name  = var.domain_name
  zone_comment = "BlueMoxon domain - managed by Terraform"

  # Landing site (bluemoxon.com, www.bluemoxon.com)
  landing_cloudfront_domain_name = var.landing_cloudfront_domain_name

  # Frontend app (app.bluemoxon.com)
  app_cloudfront_domain_name = var.app_cloudfront_domain_name

  # Staging frontend app (staging.app.bluemoxon.com)
  staging_app_cloudfront_domain_name = var.staging_app_cloudfront_domain_name

  # API Gateway (api.bluemoxon.com)
  api_domain_name    = var.api_gateway_domain_name
  api_domain_zone_id = var.api_gateway_domain_zone_id

  # Staging API Gateway (staging.api.bluemoxon.com)
  staging_api_domain_name    = var.staging_api_gateway_domain_name
  staging_api_domain_zone_id = var.staging_api_gateway_domain_zone_id

  tags = local.common_tags
}

# =============================================================================
# Outputs Reference
# =============================================================================
# See outputs.tf for all exported values
