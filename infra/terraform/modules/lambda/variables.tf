variable "environment" {
  type        = string
  description = "Environment name (staging, prod)"
}

variable "environment_variables" {
  type        = map(string)
  description = "Environment variables for the Lambda function"
  default     = {}
}

variable "function_name" {
  type        = string
  description = "Name of the Lambda function"
}

variable "handler" {
  type        = string
  description = "Lambda function handler"
  default     = "app.main.handler"
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention in days"
  default     = 14
}

variable "memory_size" {
  type        = number
  description = "Memory allocation in MB"
  default     = 512
}

variable "package_path" {
  type        = string
  description = "Path to the Lambda deployment package (optional if using s3_bucket/s3_key)"
  default     = null
}

variable "s3_bucket" {
  type        = string
  description = "S3 bucket containing the Lambda deployment package"
  default     = null
}

variable "s3_key" {
  type        = string
  description = "S3 key for the Lambda deployment package"
  default     = null
}

variable "provisioned_concurrency" {
  type        = number
  description = "Provisioned concurrency for warm starts (0 = scale to zero when idle)"
  default     = 0
}

variable "runtime" {
  type        = string
  description = "Lambda runtime"
  default     = "python3.12"
}

variable "security_group_ids" {
  type        = list(string)
  description = "Security group IDs for Lambda"
  default     = []
}

variable "source_code_hash" {
  type        = string
  description = "Base64-encoded SHA256 hash of the package file"
  default     = null
}

variable "subnet_ids" {
  type        = list(string)
  description = "VPC subnet IDs for Lambda"
  default     = []
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}

variable "timeout" {
  type        = number
  description = "Function timeout in seconds"
  default     = 30
}
