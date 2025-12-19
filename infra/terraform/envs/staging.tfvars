# =============================================================================
# Staging Environment Configuration
# =============================================================================

environment    = "staging"
aws_account_id = "652617421195"
aws_region     = "us-west-2"

# Domain configuration
domain_name   = "bluemoxon.com"
api_subdomain = "staging.api"
app_subdomain = "staging.app"

# Custom domain ACM certificates (created manually, to be imported)
# CloudFront requires us-east-1 certificate
frontend_acm_cert_arn = "arn:aws:acm:us-east-1:652617421195:certificate/cc72c0b6-da3d-4ffa-8a9d-faffeb52283f"
# API Gateway uses regional certificate (us-west-2)
api_acm_cert_arn = "arn:aws:acm:us-west-2:652617421195:certificate/2de326a8-d05e-4a54-8115-acb4e8eacc85"

# Lambda - matches production for consistent behavior
lambda_memory_size             = 512
lambda_timeout                 = 600
lambda_provisioned_concurrency = 0 # No provisioned concurrency = scale to zero

# Database - minimal for staging
enable_database      = true
db_instance_class    = "db.t3.micro"
db_allocated_storage = 20
# Note: db_password should be passed via TF_VAR_db_password or -var flag, not stored in file

# Feature flags
enable_cloudfront = true
enable_waf        = false
# GitHub OIDC - manages GitHub Actions deployment role
enable_github_oidc                 = true
enable_github_oidc_drift_detection = true # Read-only permissions for pre-deploy drift check

# Terraform state access for GitHub Actions deploy workflow
# Points to staging state bucket in same account (for reading terraform outputs during deploy)
terraform_state_bucket_arn         = "arn:aws:s3:::bluemoxon-terraform-state-staging"
terraform_state_dynamodb_table_arn = "arn:aws:dynamodb:us-west-2:652617421195:table/bluemoxon-terraform-locks"

# Cognito MFA - OPTIONAL with TOTP enabled (matches prod)
cognito_mfa_configuration = "OPTIONAL"
cognito_mfa_totp_enabled  = true

# Database sync - production secret ARN for cross-account sync
prod_database_secret_arn = "arn:aws:secretsmanager:us-west-2:266672885920:secret:bluemoxon/db-credentials-Firmtl"

# VPC Networking - NAT Gateway for Lambda outbound access (Cognito API)
enable_nat_gateway = true
public_subnet_id   = "subnet-0c5f84e98ba25334d"
private_subnet_ids = [
  "subnet-0ceb0276fa36428f2",
  "subnet-09eeb023cb49a83d5",
  "subnet-0bfb299044084bad3"
]
# Cognito VPC endpoint only supports us-west-2a/b/c (not 2d)
cognito_endpoint_subnet_ids = [
  "subnet-0ceb0276fa36428f2",
  "subnet-09eeb023cb49a83d5"
]

# =============================================================================
# Bootstrap values (explicit ARNs to break Terraform count dependencies)
# =============================================================================
# These values allow Terraform to determine counts without requiring
# cross-module references. Needed until all resources are imported into state.

# Scraper module - container-based Lambda for eBay scraping
enable_scraper = true

# Scraper Lambda ARN (used by lambda and eval_runbook_worker for invoke permissions)
scraper_lambda_arn = "arn:aws:lambda:us-west-2:652617421195:function:bluemoxon-staging-scraper"

# API Lambda security group (used by workers for VPC config)
external_lambda_security_group_id = "sg-050fb5268bcd06443"

# API Lambda role name (used by workers for SQS send permissions)
lambda_iam_role_name_override = "bluemoxon-staging-api-exec-role"

# Images CDN URL - uses branded path-based routing via frontend CDN
images_cdn_url_override = "https://staging.app.bluemoxon.com/book-images"

# =============================================================================
# Secondary Origin (Images Bucket) for /book-images/* routing
# =============================================================================
secondary_origin_bucket_name        = "bluemoxon-images-staging"
secondary_origin_bucket_domain_name = "bluemoxon-images-staging.s3.us-west-2.amazonaws.com"
secondary_origin_path_pattern       = "/book-images/*"
secondary_origin_ttl                = 604800
