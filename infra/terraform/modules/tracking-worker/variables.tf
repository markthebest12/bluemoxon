variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name (staging/production)"
  type        = string
}

variable "handler_dispatcher" {
  description = "Handler for dispatcher Lambda"
  type        = string
  default     = "app.workers.tracking_dispatcher.handler"
}

variable "handler_worker" {
  description = "Handler for worker Lambda"
  type        = string
  default     = "app.workers.tracking_worker.handler"
}

variable "runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.12"
}

variable "memory_size_dispatcher" {
  description = "Memory for dispatcher Lambda (MB)"
  type        = number
  default     = 256
}

variable "memory_size_worker" {
  description = "Memory for worker Lambda (MB)"
  type        = number
  default     = 512
}

variable "timeout_dispatcher" {
  description = "Timeout for dispatcher Lambda (seconds)"
  type        = number
  default     = 60
}

variable "timeout_worker" {
  description = "Timeout for worker Lambda (seconds)"
  type        = number
  default     = 60
}

variable "reserved_concurrency" {
  description = "Max concurrent worker executions"
  type        = number
  default     = 10
}

variable "package_path" {
  description = "Path to Lambda deployment package"
  type        = string
}

variable "source_code_hash" {
  description = "Hash of deployment package"
  type        = string
}

variable "subnet_ids" {
  description = "VPC subnet IDs"
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  description = "VPC security group IDs"
  type        = list(string)
  default     = []
}

variable "environment_variables" {
  description = "Environment variables for Lambdas"
  type        = map(string)
  default     = {}
}

variable "secrets_arns" {
  description = "ARNs of secrets to access"
  type        = list(string)
  default     = []
}

variable "log_retention_days" {
  description = "CloudWatch log retention"
  type        = number
  default     = 14
}

variable "schedule_expression" {
  description = "EventBridge schedule expression"
  type        = string
  default     = "rate(1 hour)"
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
