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

  bucket_name         = local.frontend_bucket_name
  enable_versioning   = false
  block_public_access = true
  enable_website      = false
  cloudfront_oai_arn  = var.enable_cloudfront ? module.frontend_cdn[0].oai_arn : null

  tags = local.common_tags
}

module "images_bucket" {
  source = "./modules/s3"

  bucket_name         = local.images_bucket_name
  enable_versioning   = true
  block_public_access = true
  cloudfront_oai_arn  = var.enable_cloudfront ? module.images_cdn[0].oai_arn : null

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
# Outputs Reference
# =============================================================================
# See outputs.tf for all exported values
