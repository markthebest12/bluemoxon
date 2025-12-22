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
# Needed when database is enabled OR when Lambda needs VPC connectivity
data "aws_vpc" "default" {
  count   = var.enable_database || local.enable_lambda_vpc ? 1 : 0
  default = true
}

data "aws_subnets" "default" {
  count = var.enable_database || local.enable_lambda_vpc ? 1 : 0
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

  # Allow frontend CDN to access images via secondary origin (/book-images/*)
  secondary_cloudfront_distribution_arns = var.secondary_origin_bucket_name != null ? [module.frontend_cdn[0].distribution_arn] : []

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
  s3_bucket_arn         = module.frontend_bucket.bucket_arn
  domain_aliases        = var.frontend_acm_cert_arn != null ? [local.app_domain] : []
  acm_certificate_arn   = var.frontend_acm_cert_arn
  origin_access_type    = var.cloudfront_origin_access_type
  oai_comment           = "OAI for ${local.frontend_bucket_name}"
  oac_name              = "${local.frontend_bucket_name}-oac"
  comment               = "BlueMoxon Frontend - ${var.environment}"

  # Secondary origin for images (enables /book-images/* routing)
  secondary_origin_bucket_name        = var.secondary_origin_bucket_name
  secondary_origin_bucket_domain_name = var.secondary_origin_bucket_domain_name
  secondary_origin_path_pattern       = var.secondary_origin_path_pattern
  secondary_origin_ttl                = var.secondary_origin_ttl

  tags = local.common_tags
}

module "images_cdn" {
  count  = var.enable_cloudfront && !var.cloudfront_multi_origin_enabled ? 1 : 0
  source = "./modules/cloudfront"

  s3_bucket_name        = module.images_bucket.bucket_name
  s3_bucket_domain_name = module.images_bucket.bucket_regional_domain_name
  s3_bucket_arn         = module.images_bucket.bucket_arn
  domain_aliases        = []
  acm_certificate_arn   = null
  default_root_object   = ""
  origin_access_type    = var.cloudfront_origin_access_type
  oai_comment           = "OAI for ${local.images_bucket_name}"
  oac_name              = "${local.images_bucket_name}-oac"
  comment               = "BlueMoxon Images CDN - ${var.environment}"
  default_ttl           = 604800  # 7 days for images
  max_ttl               = 2592000 # 30 days

  tags = local.common_tags
}

# =============================================================================
# Cognito User Pool
# =============================================================================

module "cognito" {
  count  = var.enable_cognito ? 1 : 0
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
  iam_role_name    = var.lambda_iam_role_name_override
  environment      = var.environment
  package_path     = var.lambda_package_path
  source_code_hash = var.lambda_source_code_hash

  runtime     = var.lambda_runtime
  memory_size = var.lambda_memory_size
  timeout     = var.lambda_timeout

  provisioned_concurrency = var.lambda_provisioned_concurrency

  # VPC configuration (when Lambda VPC is enabled)
  # Use private_subnet_ids if provided, otherwise use all default subnets
  # Use prod_vpc_id if provided, otherwise use default VPC
  create_security_group      = local.enable_lambda_vpc
  vpc_id                     = local.lambda_vpc_id
  subnet_ids                 = local.enable_lambda_vpc ? (length(var.private_subnet_ids) > 0 ? var.private_subnet_ids : data.aws_subnets.default[0].ids) : []
  security_group_name        = var.lambda_security_group_name_override
  security_group_description = var.lambda_security_group_description_override

  # Secrets Manager access
  # - If database module enabled: use module-created secret pattern
  # - If database_secret_arn provided: use explicit ARN (for prod with external Aurora)
  secrets_arns = var.enable_database ? [
    "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}/database*"
  ] : (var.database_secret_arn != null ? [var.database_secret_arn] : [])

  # S3 bucket access
  s3_bucket_arns = [module.images_bucket.bucket_arn]

  # Cognito access for user management
  # - If cognito module enabled: use module-created pool ARN
  # - If external ARN provided: use explicit ARN (for prod with external Cognito)
  cognito_user_pool_arns = var.enable_cognito ? [module.cognito[0].user_pool_arn] : (
    var.cognito_user_pool_arn_external != null ? [var.cognito_user_pool_arn_external] : []
  )

  # Bedrock model access for AI-powered features
  # - Haiku 3.5: fast, cheap extraction for listing/order parsing
  # - Sonnet/Opus: complex analysis generation
  bedrock_model_ids = [
    "anthropic.claude-3-5-haiku-20241022-v1:0",
    "anthropic.claude-sonnet-4-5-20250929-v1:0",
    "anthropic.claude-opus-4-5-20251101-v1:0"
  ]

  # Cost Explorer access for admin cost dashboard
  cost_explorer_access = true

  # Lambda invoke permissions (e.g., scraper Lambda for eBay listing scraping)
  # When scraper is Terraform-managed, scraper module creates the invoke policy
  # Only pass ARN when scraper is external (not managed by Terraform)
  lambda_invoke_arns = local.scraper_enabled ? [] : (local.scraper_lambda_arn != null ? [local.scraper_lambda_arn] : [])

  # Cost Explorer access for admin dashboard
  enable_cost_explorer_access = var.enable_cost_explorer_access

  # Environment variables using BMX_* naming convention (standard for all environments)
  environment_variables = merge(
    {
      BMX_CORS_ORIGINS          = "https://${local.app_domain},http://localhost:5173"
      BMX_IMAGES_CDN_URL        = coalesce(var.images_cdn_url_override, var.enable_cloudfront ? "https://${local.app_domain}/book-images" : "")
      BMX_COGNITO_USER_POOL_ID  = var.enable_cognito ? module.cognito[0].user_pool_id : coalesce(var.cognito_user_pool_id_external, "")
      BMX_COGNITO_CLIENT_ID     = var.enable_cognito ? module.cognito[0].client_id : coalesce(var.cognito_client_id_external, "")
      BMX_IMAGES_BUCKET         = module.images_bucket.bucket_name
      BMX_API_KEY_HASH          = var.api_key_hash
      BMX_ALLOWED_EDITOR_EMAILS = var.allowed_editor_emails
      BMX_MAINTENANCE_MODE      = var.maintenance_mode
      BMX_ENVIRONMENT           = coalesce(var.environment_name_override, var.environment)
      # Worker queue names (URLs constructed at runtime)
      BMX_ANALYSIS_QUEUE_NAME     = "${local.name_prefix}-analysis-jobs"
      BMX_EVAL_RUNBOOK_QUEUE_NAME = "${local.name_prefix}-eval-runbook-jobs"
    },
    # Database secret ARN (use module output for staging, explicit ARN for prod)
    var.enable_database ? {
      BMX_DATABASE_SECRET_ARN = module.database_secret[0].arn
      } : (var.database_secret_arn != null ? {
        BMX_DATABASE_SECRET_ARN = var.database_secret_arn
    } : {})
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
  cognito_user_pool_id  = module.cognito[0].user_pool_id
  enable_cognito_access = var.enable_cognito

  environment_variables = {
    PROD_SECRET_ARN      = var.prod_database_secret_arn
    STAGING_SECRET_ARN   = module.database_secret[0].arn
    PROD_SECRET_REGION   = "us-west-2"
    COGNITO_USER_POOL_ID = module.cognito[0].user_pool_id
  }

  tags = local.common_tags

  depends_on = [module.database_secret]
}

# =============================================================================
# Scraper Lambda (Playwright-based eBay scraping)
# =============================================================================

module "scraper_lambda" {
  count  = local.scraper_enabled ? 1 : 0
  source = "./modules/scraper-lambda"

  name_prefix = local.name_prefix
  environment = var.environment

  # Name overrides for legacy naming (prod uses different pattern)
  ecr_repository_name_override = var.scraper_ecr_repository_name_override
  function_name_override       = var.scraper_function_name_override
  iam_role_name_override       = var.scraper_iam_role_name_override

  # Allow API Lambda to invoke scraper
  api_lambda_role_name = module.lambda[0].role_name
  api_lambda_role_arn  = module.lambda[0].role_arn

  # S3 bucket for scraped images
  images_bucket_arn  = module.images_bucket.bucket_arn
  images_bucket_name = module.images_bucket.bucket_name

  # Scraper settings
  image_tag   = "v1.0.7"
  memory_size = var.scraper_memory_size
  timeout     = 120 # Production uses 120s (Playwright + S3 uploads)

  # Override ENVIRONMENT for prod (uses "production" not "prod")
  environment_variables = {
    ENVIRONMENT = coalesce(var.environment_name_override, var.environment)
  }

  tags = local.common_tags
}

# =============================================================================
# Analysis Worker (async Bedrock analysis with SQS)
# =============================================================================
# Can be enabled independently of main Lambda using enable_analysis_worker.
# When enable_lambda=false, uses external_lambda_role_name and
# external_lambda_security_group_id for permissions and VPC config.

module "analysis_worker" {
  count  = local.analysis_worker_enabled ? 1 : 0
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
  reserved_concurrency = -1 # No reservation (account has low concurrency limit)

  # VPC configuration - use external security group if Lambda is managed externally
  subnet_ids         = var.private_subnet_ids
  security_group_ids = local.lambda_security_group_id != null ? [local.lambda_security_group_id] : []

  # Secrets Manager access - use prod secret ARN pattern for external Lambda
  secrets_arns = var.enable_database ? [
    "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}/database*"
    ] : (
    # For prod with external Lambda, use the secret ARN pattern directly
    local.is_prod ? [
      "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:bluemoxon/db-credentials*"
    ] : []
  )

  # S3 bucket access
  s3_bucket_arns = [module.images_bucket.bucket_arn]

  # Bedrock model access (wildcards to cover all versions)
  bedrock_model_ids = [
    "anthropic.claude-sonnet-4-5-*",
    "anthropic.claude-opus-4-5-*"
  ]

  # Allow API Lambda to send messages to SQS - use external role if Lambda disabled
  api_lambda_role_name = local.api_lambda_role_name

  # Environment variables
  environment_variables = merge(
    {
      IMAGES_CDN_DOMAIN = var.enable_cloudfront ? module.images_cdn[0].distribution_domain_name : ""
      IMAGES_BUCKET     = module.images_bucket.bucket_name
    },
    # Database secret ARN (use module output for staging, explicit ARN for prod)
    var.enable_database ? {
      DATABASE_SECRET_ARN = module.database_secret[0].arn
      } : (var.database_secret_arn != null ? {
        DATABASE_SECRET_ARN = var.database_secret_arn
    } : {})
  )

  tags = local.common_tags
}

# =============================================================================
# Eval Runbook Worker (async eval runbook generation with SQS)
# =============================================================================
# Can be enabled independently of main Lambda using enable_eval_runbook_worker.
# When enable_lambda=false, uses external_lambda_role_name and
# external_lambda_security_group_id for permissions and VPC config.

module "eval_runbook_worker" {
  count  = local.eval_runbook_worker_enabled ? 1 : 0
  source = "./modules/eval-runbook-worker"

  name_prefix = local.name_prefix
  environment = var.environment

  package_path     = var.lambda_package_path
  source_code_hash = var.lambda_source_code_hash
  runtime          = var.lambda_runtime

  # Match API Lambda timeout + buffer for SQS visibility
  timeout              = 600
  visibility_timeout   = 660
  memory_size          = 256
  reserved_concurrency = -1 # No reservation (account has low concurrency limit)

  # VPC configuration - use external security group if Lambda is managed externally
  subnet_ids         = var.private_subnet_ids
  security_group_ids = local.lambda_security_group_id != null ? [local.lambda_security_group_id] : []

  # Secrets Manager access - use prod secret ARN pattern for external Lambda
  secrets_arns = var.enable_database ? [
    "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}/database*"
    ] : (
    # For prod with external Lambda, use the secret ARN pattern directly
    local.is_prod ? [
      "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:bluemoxon/db-credentials*"
    ] : []
  )

  # S3 bucket access
  s3_bucket_arns = [module.images_bucket.bucket_arn]

  # Bedrock model access (wildcards to cover all versions)
  # Uses Haiku for fast attribute extraction in eval runbook
  bedrock_model_ids = [
    "anthropic.claude-3-5-haiku-*",
    "anthropic.claude-sonnet-4-5-*"
  ]

  # Lambda invoke permissions (e.g., scraper Lambda for eBay FMV lookup)
  lambda_invoke_arns = local.scraper_lambda_arn != null ? [local.scraper_lambda_arn] : []

  # Allow API Lambda to send messages to SQS - use external role if Lambda disabled
  api_lambda_role_name = local.api_lambda_role_name

  # Environment variables
  environment_variables = merge(
    {
      IMAGES_CDN_DOMAIN = var.enable_cloudfront ? module.images_cdn[0].distribution_domain_name : ""
      IMAGES_BUCKET     = module.images_bucket.bucket_name
    },
    # Database secret ARN (use module output for staging, explicit ARN for prod)
    var.enable_database ? {
      DATABASE_SECRET_ARN = module.database_secret[0].arn
      } : (var.database_secret_arn != null ? {
        DATABASE_SECRET_ARN = var.database_secret_arn
    } : {})
  )

  tags = local.common_tags
}

# =============================================================================
# API Gateway
# =============================================================================

module "api_gateway" {
  count  = var.enable_api_gateway ? 1 : 0
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

  # ECR permissions for scraper deployment
  ecr_repository_arns = local.scraper_enabled ? [module.scraper_lambda[0].ecr_repository_arn] : []

  # Terraform state access (cross-account for staging to read prod state)
  terraform_state_bucket_arn         = var.terraform_state_bucket_arn
  terraform_state_dynamodb_table_arn = var.terraform_state_dynamodb_table_arn

  # Enable read-only permissions for Terraform drift detection during deploys
  enable_terraform_drift_detection = var.enable_github_oidc_drift_detection

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
