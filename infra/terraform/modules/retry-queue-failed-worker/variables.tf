# =============================================================================
# Retry Queue Failed Worker Module Variables
# =============================================================================

variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "environment" {
  description = "Environment (staging, production)"
  type        = string
}

variable "handler" {
  description = "Lambda handler function"
  type        = string
  default     = "lambdas.retry_queue_failed.handler.handler"
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
  description = "Lambda timeout in seconds"
  type        = number
  default     = 60
}

variable "s3_bucket" {
  description = "S3 bucket containing the Lambda deployment package"
  type        = string
}

variable "s3_key" {
  description = "S3 key (path) to the Lambda deployment package"
  type        = string
}

variable "environment_variables" {
  description = "Environment variables for the Lambda function"
  type        = map(string)
  default     = {}
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

# VPC configuration
variable "subnet_ids" {
  description = "VPC subnet IDs for Lambda"
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  description = "Security group IDs for Lambda"
  type        = list(string)
  default     = []
}

# IAM access
variable "secret_arns" {
  description = "ARNs of secrets the Lambda can access"
  type        = list(string)
  default     = []
}

variable "sqs_queue_arns" {
  description = "ARNs of SQS queues the Lambda can access"
  type        = list(string)
  default     = []
}

# Scheduling
variable "schedule_expression" {
  description = "EventBridge schedule expression (e.g., 'rate(5 minutes)')"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "layers" {
  description = "List of Lambda Layer ARNs to attach"
  type        = list(string)
  default     = []
}
