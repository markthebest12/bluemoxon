# =============================================================================
# Analysis Worker Module Variables
# =============================================================================

variable "name_prefix" {
  description = "Prefix for resource names (e.g., bluemoxon-staging)"
  type        = string
}

variable "environment" {
  description = "Environment name (staging, prod)"
  type        = string
}

# -----------------------------------------------------------------------------
# Lambda Configuration
# -----------------------------------------------------------------------------

variable "handler" {
  description = "Lambda handler function"
  type        = string
  default     = "app.worker.handler"
}

variable "runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.12"
}

variable "memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 256
}

variable "timeout" {
  description = "Lambda timeout in seconds (max 900 for SQS-triggered)"
  type        = number
  default     = 600
}

variable "reserved_concurrency" {
  description = "Reserved concurrent executions (limits parallel Bedrock calls)"
  type        = number
  default     = 5
}

variable "s3_bucket" {
  description = "S3 bucket containing the Lambda deployment package"
  type        = string
}

variable "s3_key" {
  description = "S3 key (path) to the Lambda deployment package"
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 14
}

# -----------------------------------------------------------------------------
# SQS Configuration
# -----------------------------------------------------------------------------

variable "visibility_timeout" {
  description = "SQS visibility timeout in seconds (should be >= Lambda timeout)"
  type        = number
  default     = 660 # Lambda timeout + 60s buffer
}

variable "max_receive_count" {
  description = "Max retries before message goes to DLQ"
  type        = number
  default     = 2
}

# -----------------------------------------------------------------------------
# VPC Configuration
# -----------------------------------------------------------------------------

variable "subnet_ids" {
  description = "Subnet IDs for Lambda VPC configuration"
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  description = "Security group IDs for Lambda VPC configuration"
  type        = list(string)
  default     = []
}

# -----------------------------------------------------------------------------
# IAM / Permissions
# -----------------------------------------------------------------------------

variable "secrets_arns" {
  description = "ARNs of Secrets Manager secrets to access"
  type        = list(string)
  default     = []
}

variable "s3_bucket_arns" {
  description = "ARNs of S3 buckets to access"
  type        = list(string)
  default     = []
}

variable "bedrock_model_ids" {
  description = "Bedrock model IDs to allow invocation"
  type        = list(string)
  default     = []
}

variable "api_lambda_role_name" {
  description = "Name of API Lambda's IAM role (for SQS send permission)"
  type        = string
  default     = null
}

# -----------------------------------------------------------------------------
# Environment Variables
# -----------------------------------------------------------------------------

variable "environment_variables" {
  description = "Environment variables for Lambda function"
  type        = map(string)
  default     = {}
}

# -----------------------------------------------------------------------------
# Tags
# -----------------------------------------------------------------------------

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
