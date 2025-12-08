# =============================================================================
# Production Environment Configuration
# =============================================================================

environment    = "prod"
aws_account_id = "266672885920"
aws_region     = "us-west-2"

# Domain configuration
domain_name   = "bluemoxon.com"
api_subdomain = "api"
app_subdomain = "app"

# Lambda - production sizing with warm starts
lambda_memory_size             = 512
lambda_timeout                 = 30
lambda_provisioned_concurrency = 1 # Keep 1 instance warm to avoid cold starts

# Database - production sizing
db_instance_class    = "db.t3.small"
db_allocated_storage = 50

# Feature flags
enable_cloudfront = true
enable_waf        = true

# GitHub OIDC - Override bucket ARNs for legacy naming convention
# Prod uses bluemoxon-frontend/bluemoxon-images instead of bluemoxon-prod-frontend
github_oidc_frontend_bucket_arns = ["arn:aws:s3:::bluemoxon-frontend"]
github_oidc_images_bucket_arns   = ["arn:aws:s3:::bluemoxon-images"]
github_oidc_cloudfront_distribution_arns = [
  "arn:aws:cloudfront::266672885920:distribution/E16BJX90QWQNQO"
]
