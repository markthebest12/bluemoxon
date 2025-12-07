variable "create_security_group" {
  type        = bool
  description = "Create a security group for the Lambda function (requires vpc_id)"
  default     = false
}

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
  description = "Path to the Lambda deployment package"
}

variable "provisioned_concurrency" {
  type        = number
  description = "Provisioned concurrency for warm starts (0 = scale to zero when idle)"
  default     = 0
}

variable "runtime" {
  type        = string
  description = "Lambda runtime"
  default     = "python3.11"
}

variable "s3_bucket_arns" {
  type        = list(string)
  description = "S3 bucket ARNs the Lambda function can access"
  default     = []
}

variable "secrets_arns" {
  type        = list(string)
  description = "Secrets Manager secret ARNs the Lambda function can access"
  default     = []
}

variable "security_group_ids" {
  type        = list(string)
  description = "Additional security group IDs for Lambda VPC configuration"
  default     = []
}

variable "source_code_hash" {
  type        = string
  description = "Base64-encoded SHA256 hash of the package file"
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

variable "vpc_id" {
  type        = string
  description = "VPC ID for the Lambda security group (required if create_security_group is true)"
  default     = null
}
