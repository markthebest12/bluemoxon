# =============================================================================
# Environment Configuration
# =============================================================================

variable "environment" {
  description = "Environment name (staging, prod)"
  type        = string

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "Environment must be 'staging' or 'prod'."
  }
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-west-2"
}

variable "aws_account_id" {
  description = "AWS account ID for the target environment"
  type        = string
}

# =============================================================================
# Application Configuration
# =============================================================================

variable "app_name" {
  description = "Application name used for resource naming"
  type        = string
  default     = "bluemoxon"
}

variable "domain_name" {
  description = "Primary domain name for the application"
  type        = string
}

variable "api_subdomain" {
  description = "Subdomain for the API (e.g., 'api' or 'staging-api')"
  type        = string
}

variable "app_subdomain" {
  description = "Subdomain for the frontend app (e.g., 'app' or 'staging')"
  type        = string
}

# =============================================================================
# Lambda Configuration
# =============================================================================

variable "lambda_memory_size" {
  description = "Memory allocation for Lambda function (MB)"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Lambda function timeout (seconds)"
  type        = number
  default     = 30
}

variable "lambda_runtime" {
  description = "Lambda runtime version"
  type        = string
  default     = "python3.12"
}

variable "lambda_provisioned_concurrency" {
  description = "Provisioned concurrency for Lambda (0 = scale to zero when idle)"
  type        = number
  default     = 0
}

# =============================================================================
# Database Configuration
# =============================================================================

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage (GB)"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "bluemoxon"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "bluemoxon"
  sensitive   = true
}

variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}

# =============================================================================
# Feature Flags
# =============================================================================

variable "enable_cloudfront" {
  description = "Enable CloudFront distribution"
  type        = bool
  default     = true
}

variable "enable_waf" {
  description = "Enable WAF for API Gateway"
  type        = bool
  default     = false
}
