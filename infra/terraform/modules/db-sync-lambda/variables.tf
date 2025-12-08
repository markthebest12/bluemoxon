variable "environment_variables" {
  type        = map(string)
  description = "Environment variables for the Lambda"
  default     = {}
}

variable "function_name" {
  type        = string
  description = "Name of the Lambda function"
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention in days"
  default     = 14
}

variable "memory_size" {
  type        = number
  description = "Memory size in MB"
  default     = 512
}

variable "package_path" {
  type        = string
  description = "Path to the Lambda deployment package"
  default     = "db-sync-lambda.zip"
}

variable "runtime" {
  type        = string
  description = "Lambda runtime"
  default     = "python3.12"
}

variable "secret_arns" {
  type        = list(string)
  description = "ARNs of secrets the Lambda needs to access"
}

variable "security_group_ids" {
  type        = list(string)
  description = "Security group IDs for VPC configuration"
}

variable "source_code_hash" {
  type        = string
  description = "Base64-encoded SHA256 hash of the package"
  default     = ""
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for VPC configuration"
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}

variable "timeout" {
  type        = number
  description = "Timeout in seconds"
  default     = 900
}
