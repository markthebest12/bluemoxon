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

variable "enable_database" {
  type        = bool
  description = "Enable RDS PostgreSQL database"
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

variable "lambda_memory_size" {
  type        = number
  description = "Memory allocation for Lambda function (MB)"
  default     = 512
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

variable "prod_database_secret_arn" {
  type        = string
  description = "ARN of the production database secret (for staging sync Lambda)"
  default     = ""
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
