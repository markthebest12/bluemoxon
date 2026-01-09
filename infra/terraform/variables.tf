variable "api_subdomain" {
  type        = string
  description = "Subdomain for the API (e.g., 'api' or 'staging-api')"
}

variable "app_name" {
  type        = string
  description = "Application name used for resource naming"
  default     = "bluemoxon"
}

variable "app_subdomain" {
  type        = string
  description = "Subdomain for the frontend app (e.g., 'app' or 'staging')"
}

variable "aws_account_id" {
  type        = string
  description = "AWS account ID for the target environment"
}

variable "aws_region" {
  type        = string
  description = "AWS region for all resources"
  default     = "us-west-2"
}

variable "cognito_mfa_configuration" {
  type        = string
  description = "Cognito MFA configuration: OFF, ON, or OPTIONAL"
  default     = "OFF"
}

variable "cognito_mfa_totp_enabled" {
  type        = bool
  description = "Enable TOTP (software token) MFA for Cognito"
  default     = false
}

variable "cognito_endpoint_subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for Cognito VPC endpoint (must be in AZs supported by Cognito: us-west-2a/b/c). Falls back to private_subnet_ids if empty."
  default     = []
}

variable "db_allocated_storage" {
  type        = number
  description = "RDS allocated storage (GB)"
  default     = 20
}

variable "db_instance_class" {
  type        = string
  description = "RDS instance class"
  default     = "db.t3.micro"
}

variable "db_name" {
  type        = string
  description = "Database name"
  default     = "bluemoxon"
}

variable "db_password" {
  type        = string
  description = "Database master password"
  sensitive   = true
}

variable "database_secret_arn" {
  type        = string
  description = "Explicit database secret ARN (for prod where database is managed externally)"
  default     = null
}

variable "db_username" {
  type        = string
  description = "Database master username"
  default     = "bluemoxon"
  sensitive   = true
}

variable "domain_name" {
  type        = string
  description = "Primary domain name for the application"
}

variable "enable_cloudfront" {
  type        = bool
  description = "Enable CloudFront distribution"
  default     = true
}

variable "cloudfront_origin_access_type" {
  type        = string
  description = "Type of S3 origin access for CloudFront: 'oai' (legacy Origin Access Identity) or 'oac' (modern Origin Access Control)"
  default     = "oai"

  validation {
    condition     = contains(["oai", "oac"], var.cloudfront_origin_access_type)
    error_message = "cloudfront_origin_access_type must be 'oai' or 'oac'"
  }
}

variable "enable_cognito" {
  type        = bool
  description = "Enable Cognito user pool management (set false for prod where Cognito is managed externally)"
  default     = true
}

variable "enable_database" {
  type        = bool
  description = "Enable RDS PostgreSQL database"
  default     = false
}

variable "enable_lambda" {
  type        = bool
  description = "Enable Lambda function management (set false for prod where Lambda is managed externally)"
  default     = true
}

variable "enable_lambda_vpc" {
  type        = bool
  description = "Enable Lambda VPC configuration (for database connectivity). Defaults to enable_database if not set."
  default     = null
}

variable "enable_cost_explorer_access" {
  type        = bool
  description = "Enable AWS Cost Explorer access for admin dashboard cost monitoring"
  default     = false
}

variable "lambda_function_name_external" {
  type        = string
  description = "External Lambda function name (used when enable_lambda=false)"
  default     = null
}

variable "lambda_invoke_arn_external" {
  type        = string
  description = "External Lambda invoke ARN (used when enable_lambda=false)"
  default     = null
}

variable "scraper_lambda_arn" {
  type        = string
  description = "ARN of scraper Lambda function that API Lambda can invoke"
  default     = null
}

variable "enable_scraper" {
  type        = bool
  description = "Enable scraper Lambda module (container-based Playwright scraper). Set false when using existing scraper."
  default     = null # Defaults to enable_lambda value when null
}

variable "scraper_ecr_repository_name_override" {
  type        = string
  description = "Override scraper ECR repository name (for legacy naming)"
  default     = null
}

variable "scraper_function_name_override" {
  type        = string
  description = "Override scraper Lambda function name (for legacy naming)"
  default     = null
}

variable "scraper_iam_role_name_override" {
  type        = string
  description = "Override scraper IAM role name (for legacy naming)"
  default     = null
}

variable "scraper_memory_size" {
  type        = number
  description = "Scraper Lambda memory in MB. Playwright/Chromium needs 2048+ for complex pages."
  default     = 2048
}

variable "enable_analysis_worker" {
  type        = bool
  description = "Enable analysis worker Lambda + SQS (can be enabled independently of main Lambda)"
  default     = null # Defaults to enable_lambda value when null
}

variable "enable_eval_runbook_worker" {
  type        = bool
  description = "Enable eval runbook worker Lambda + SQS (can be enabled independently of main Lambda)"
  default     = null # Defaults to enable_lambda value when null
}

variable "enable_cleanup_lambda" {
  type        = bool
  description = "Enable cleanup Lambda for stale data maintenance"
  default     = null # Defaults to enable_lambda value when null
}

variable "cleanup_schedule_expression" {
  type        = string
  description = "EventBridge schedule expression for cleanup Lambda (e.g., 'rate(1 day)')"
  default     = null # No schedule by default - triggered via admin API
}

variable "cleanup_function_name_override" {
  type        = string
  description = "Override cleanup Lambda function name (for legacy naming, e.g., bluemoxon-production-cleanup)"
  default     = null
}

variable "enable_tracking_worker" {
  type        = bool
  description = "Enable tracking worker Lambda + SQS for async tracking updates (can be enabled independently of main Lambda)"
  default     = null # Defaults to enable_lambda value when null
}

variable "tracking_schedule_expression" {
  type        = string
  description = "EventBridge schedule expression for tracking dispatcher (e.g., 'rate(1 hour)')"
  default     = "rate(1 hour)"
}

variable "external_lambda_role_name" {
  type        = string
  description = "External Lambda IAM role name for SQS send permissions (used when enable_lambda=false)"
  default     = null
}

variable "external_lambda_security_group_id" {
  type        = string
  description = "External Lambda security group ID for worker VPC config (used when enable_lambda=false)"
  default     = null
}

variable "enable_nat_gateway" {
  type        = bool
  description = "Enable NAT Gateway for Lambda outbound internet access"
  default     = false
}

variable "enable_waf" {
  type        = bool
  description = "Enable WAF for API Gateway"
  default     = false
}

variable "environment" {
  type        = string
  description = "Environment name (staging, prod)"

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "Environment must be 'staging' or 'prod'."
  }
}

variable "environment_name_override" {
  type        = string
  description = "Override for BMX_ENVIRONMENT env var (e.g., 'production' instead of 'prod')"
  default     = null
}

variable "scraper_environment_override" {
  type        = string
  description = "Override for BMX_SCRAPER_ENVIRONMENT env var used to build scraper Lambda function name. Set to 'prod' when scraper Lambda is named bluemoxon-prod-scraper but BMX_ENVIRONMENT is 'production'."
  default     = null
}

variable "lambda_memory_size" {
  type        = number
  description = "Memory allocation for Lambda function (MB)"
  default     = 512
}

variable "logs_bucket_name" {
  type        = string
  description = "Name of the logs bucket for CloudFront/S3 access logs (prod only)"
  default     = null
}

variable "lambda_provisioned_concurrency" {
  type        = number
  description = "Provisioned concurrency for Lambda (0 = scale to zero when idle)"
  default     = 0
}

variable "lambda_runtime" {
  type        = string
  description = "Lambda runtime version"
  default     = "python3.12"
}

variable "lambda_package_path" {
  type        = string
  description = "Path to the Lambda deployment package"
  default     = "lambda.zip"
}

variable "lambda_source_code_hash" {
  type        = string
  description = "Base64-encoded SHA256 hash of the Lambda package"
  default     = ""
}

variable "lambda_timeout" {
  type        = number
  description = "Lambda function timeout (seconds)"
  default     = 30
}

variable "maintenance_mode" {
  type        = string
  description = "Maintenance mode flag (true/false as string)"
  default     = "false"
}

variable "allowed_editor_emails" {
  type        = string
  description = "Comma-separated list of allowed editor email addresses"
  default     = ""
}

variable "api_key_hash" {
  type        = string
  description = "SHA256 hash of the API key for authentication bypass"
  default     = ""
  sensitive   = true
}

variable "api_key" {
  type        = string
  description = "Static API key for CLI/automation access (plaintext, for legacy/dev use)"
  default     = ""
  sensitive   = true
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for Lambda VPC configuration (subnets with NAT Gateway route)"
  default     = []
}

variable "prod_vpc_id" {
  type        = string
  description = "VPC ID for prod Lambda (overrides default VPC lookup). Use when prod has dedicated VPC."
  default     = null
}

variable "prod_database_secret_arn" {
  type        = string
  description = "ARN of the production database secret (for staging sync Lambda)"
  default     = ""
}

variable "public_subnet_id" {
  type        = string
  description = "Public subnet ID where NAT Gateway will be placed (must have IGW route)"
  default     = null
}

variable "frontend_acm_cert_arn" {
  type        = string
  description = "ACM certificate ARN for CloudFront (must be in us-east-1)"
  default     = null
}

variable "api_acm_cert_arn" {
  type        = string
  description = "ACM certificate ARN for API Gateway custom domain (regional)"
  default     = null
}

# =============================================================================
# CloudFront Configuration (Multi-Origin Support)
# =============================================================================

variable "cloudfront_multi_origin_enabled" {
  type        = bool
  description = "Enable multi-origin CloudFront distribution (production uses this pattern)"
  default     = false
}

variable "cloudfront_images_path_pattern" {
  type        = string
  description = "Path pattern for images origin in multi-origin distribution"
  default     = "/book-images/*"
}

variable "cloudfront_images_oac_id" {
  type        = string
  description = "OAC ID for images origin (when importing existing multi-origin distribution)"
  default     = null
}

variable "cloudfront_function_arn" {
  type        = string
  description = "ARN of CloudFront function for path rewriting (production uses this)"
  default     = null
}

variable "images_cdn_url_override" {
  type        = string
  description = "Explicit images CDN URL (used when enable_cloudfront=false, e.g., https://app.bluemoxon.com/book-images)"
  default     = null
}

# =============================================================================
# GitHub OIDC Variables
# =============================================================================

variable "enable_api_gateway" {
  type        = bool
  description = "Enable API Gateway management (set false for prod where API Gateway is managed externally)"
  default     = true
}

variable "enable_github_oidc" {
  type        = bool
  description = "Enable GitHub Actions OIDC provider and IAM role"
  default     = true
}

variable "enable_github_oidc_drift_detection" {
  type        = bool
  description = "Enable read-only permissions for Terraform drift detection during deploys"
  default     = false
}

variable "github_oidc_cloudfront_distribution_arns" {
  type        = list(string)
  description = "CloudFront distribution ARNs for GitHub Actions deployment (override for legacy resources)"
  default     = []
}

variable "github_oidc_frontend_bucket_arns" {
  type        = list(string)
  description = "Frontend S3 bucket ARNs for GitHub Actions deployment (override for legacy resources)"
  default     = []
}

variable "github_oidc_images_bucket_arns" {
  type        = list(string)
  description = "Images S3 bucket ARNs for GitHub Actions deployment (override for legacy resources)"
  default     = []
}

variable "github_repo" {
  type        = string
  description = "GitHub repository in format 'owner/repo'"
  default     = "markthebest12/bluemoxon"
}

variable "terraform_state_bucket_arn" {
  type        = string
  description = "ARN of the Terraform state S3 bucket for cross-account access (prod account)"
  default     = null
}

variable "terraform_state_dynamodb_table_arn" {
  type        = string
  description = "ARN of the Terraform state DynamoDB lock table for cross-account access (prod account)"
  default     = null
}

# =============================================================================
# Legacy Resource Name Overrides (for production)
# =============================================================================
# Production was created before environment-suffixed naming convention.
# These overrides allow Terraform to manage existing resources without renaming.

variable "frontend_bucket_name_override" {
  type        = string
  description = "Override S3 frontend bucket name (for legacy resources without env suffix)"
  default     = null
}

variable "images_bucket_name_override" {
  type        = string
  description = "Override S3 images bucket name (for legacy resources without env suffix)"
  default     = null
}

variable "lambda_function_name_override" {
  type        = string
  description = "Override Lambda function name (for legacy resources without env suffix)"
  default     = null
}

variable "lambda_iam_role_name_override" {
  type        = string
  description = "Override Lambda IAM role name (for legacy resources with different naming pattern)"
  default     = null
}

variable "lambda_security_group_description_override" {
  type        = string
  description = "Override Lambda security group description (for legacy resources with different naming pattern)"
  default     = null
}

variable "lambda_security_group_name_override" {
  type        = string
  description = "Override Lambda security group name (for legacy resources with different naming pattern)"
  default     = null
}

variable "api_gateway_name_override" {
  type        = string
  description = "Override API Gateway name (for legacy resources without env suffix)"
  default     = null
}

variable "cognito_user_pool_name_override" {
  type        = string
  description = "Override Cognito user pool name (for legacy resources without env suffix)"
  default     = null
}

variable "cognito_domain_override" {
  type        = string
  description = "Override Cognito domain prefix (for legacy resources without env suffix)"
  default     = null
}

variable "cognito_user_pool_id_external" {
  type        = string
  description = "External Cognito user pool ID (used when enable_cognito=false)"
  default     = null
}

variable "cognito_client_id_external" {
  type        = string
  description = "External Cognito client ID (used when enable_cognito=false)"
  default     = null
}

variable "cognito_user_pool_arn_external" {
  type        = string
  description = "External Cognito user pool ARN for Lambda IAM permissions (used when enable_cognito=false)"
  default     = null
}

variable "cognito_client_name_override" {
  type        = string
  description = "Override Cognito client name (for legacy resources)"
  default     = null
}

variable "cognito_callback_urls_override" {
  type        = list(string)
  description = "Override Cognito callback URLs (for legacy resources with different URL patterns)"
  default     = null
}

variable "cognito_logout_urls_override" {
  type        = list(string)
  description = "Override Cognito logout URLs (for legacy resources with different URL patterns)"
  default     = null
}

variable "cognito_password_require_symbols" {
  type        = bool
  description = "Require symbols in Cognito passwords"
  default     = true
}

variable "cognito_allow_admin_create_user_only" {
  type        = bool
  description = "Only allow admin to create Cognito users"
  default     = false
}

variable "cognito_invite_email_message" {
  type        = string
  description = "Cognito email invitation message template"
  default     = null
}

variable "cognito_invite_email_subject" {
  type        = string
  description = "Cognito email invitation subject"
  default     = "Your temporary password"
}

variable "skip_s3_cloudfront_policy" {
  type        = bool
  description = "Skip creating OAI-based S3 bucket policies (for prod which uses OAC instead)"
  default     = false
}

# =============================================================================
# Landing Site Variables (prod only)
# =============================================================================

variable "enable_landing_site" {
  type        = bool
  description = "Enable landing site S3 + CloudFront (bluemoxon.com marketing site)"
  default     = false
}

variable "landing_acm_cert_arn" {
  type        = string
  description = "ACM certificate ARN for landing site CloudFront (must be in us-east-1)"
  default     = null
}

variable "landing_bucket_name" {
  type        = string
  description = "S3 bucket name for landing site"
  default     = null
}

variable "landing_cloudfront_domain_name" {
  type        = string
  description = "CloudFront distribution domain name for landing site (DNS alias target)"
  default     = null
}

# =============================================================================
# DNS Variables (prod only - manages Route53 for all environments)
# =============================================================================

variable "enable_dns" {
  type        = bool
  description = "Enable Route53 DNS management (prod only - DNS is centralized in prod account)"
  default     = false
}

variable "api_gateway_domain_name" {
  type        = string
  description = "API Gateway custom domain name for api.{domain} (target for Route53 alias)"
  default     = null
}

variable "api_gateway_domain_zone_id" {
  type        = string
  description = "API Gateway hosted zone ID for api.{domain}"
  default     = null
}

variable "app_cloudfront_domain_name" {
  type        = string
  description = "CloudFront distribution domain name for app.{domain} (DNS alias target)"
  default     = null
}

variable "staging_api_gateway_domain_name" {
  type        = string
  description = "API Gateway custom domain name for staging.api.{domain}"
  default     = null
}

variable "staging_api_gateway_domain_zone_id" {
  type        = string
  description = "API Gateway hosted zone ID for staging.api.{domain}"
  default     = null
}

variable "staging_app_cloudfront_domain_name" {
  type        = string
  description = "CloudFront distribution domain name for staging.app.{domain}"
  default     = null
}

# =============================================================================
# Secondary Origin (Images Bucket) Configuration
# =============================================================================

variable "secondary_origin_bucket_name" {
  type        = string
  description = "Name of secondary S3 bucket for images (optional)"
  default     = null
}

variable "secondary_origin_bucket_domain_name" {
  type        = string
  description = "Regional domain name of secondary S3 bucket"
  default     = null
}

variable "secondary_origin_path_pattern" {
  type        = string
  description = "Path pattern for secondary origin (e.g., '/book-images/*')"
  default     = null
}

variable "secondary_origin_ttl" {
  type        = number
  description = "Default TTL for secondary origin cache behavior in seconds"
  default     = 604800
}

# =============================================================================
# Entity Validation (#967, #969)
# =============================================================================

variable "entity_validation_mode" {
  type        = string
  description = "Entity validation mode: 'log' (warn but allow) or 'enforce' (reject with 409)"
  default     = "enforce"
}

variable "entity_match_threshold_publisher" {
  type        = number
  description = "Fuzzy match threshold for publishers (0.0-1.0)"
  default     = 0.80
}

variable "entity_match_threshold_binder" {
  type        = number
  description = "Fuzzy match threshold for binders (0.0-1.0)"
  default     = 0.80
}

variable "entity_match_threshold_author" {
  type        = number
  description = "Fuzzy match threshold for authors (0.0-1.0, lower due to name variations)"
  default     = 0.75
}
