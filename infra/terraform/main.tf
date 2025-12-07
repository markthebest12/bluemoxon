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
  allowed_security_group_id = module.lambda.security_group_id

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
  create_security_group = var.enable_database
  vpc_id                = var.enable_database ? data.aws_vpc.default[0].id : null
  subnet_ids            = var.enable_database ? data.aws_subnets.default[0].ids : []

  # Secrets Manager access (use ARN pattern to avoid circular dependency)
  secrets_arns = var.enable_database ? [
    "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}/database*"
  ] : []

  # S3 bucket access
  s3_bucket_arns = [module.images_bucket.bucket_arn]

  # Environment variables (secret ARN set after database_secret is created)
  environment_variables = merge(
    {
      CORS_ORIGINS          = "https://${local.app_domain},http://localhost:5173"
      IMAGES_CDN_DOMAIN     = var.enable_cloudfront ? module.images_cdn[0].distribution_domain_name : ""
      COGNITO_USER_POOL_ID   = module.cognito.user_pool_id
      COGNITO_APP_CLIENT_ID  = module.cognito.client_id
      IMAGES_BUCKET          = module.images_bucket.bucket_name
      API_KEY_HASH          = var.api_key_hash
      ALLOWED_EDITOR_EMAILS = var.allowed_editor_emails
      MAINTENANCE_MODE      = var.maintenance_mode
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
  count  = var.enable_database && !local.is_prod ? 1 : 0
  source = "./modules/db-sync-lambda"

  function_name = "${local.name_prefix}-db-sync"

  subnet_ids         = data.aws_subnets.default[0].ids
  security_group_ids = [module.lambda.security_group_id]

  # Access to both prod and staging secrets
  secret_arns = [
    # Staging secret
    "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}/database*",
    # Production secret (cross-account, requires resource policy on prod secret)
    var.prod_database_secret_arn
  ]

  environment_variables = {
    PROD_SECRET_ARN    = var.prod_database_secret_arn
    STAGING_SECRET_ARN = module.database_secret[0].arn
    PROD_SECRET_REGION = "us-west-2"
  }

  tags = local.common_tags

  depends_on = [module.database_secret]
}

# =============================================================================
# API Gateway
# =============================================================================

module "api_gateway" {
  source = "./modules/api-gateway"

  api_name             = local.api_gateway_name
  lambda_function_name = module.lambda.function_name
  lambda_invoke_arn    = module.lambda.invoke_arn

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
# Outputs Reference
# =============================================================================
# See outputs.tf for all exported values
