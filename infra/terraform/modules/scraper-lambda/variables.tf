variable "api_lambda_role_arn" {
  type        = string
  description = "ARN of the API Lambda role (for invoke permission)"
  default     = null
}

variable "api_lambda_role_name" {
  type        = string
  description = "Name of the API Lambda role (for IAM policy attachment)"
  default     = null
}

variable "enable_api_invoke_permission" {
  type        = bool
  description = "Whether to create IAM policy for API Lambda to invoke scraper"
  default     = true
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

variable "image_tag" {
  type        = string
  description = "Docker image tag to deploy"
  default     = "latest"
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention in days"
  default     = 14
}

variable "memory_size" {
  type        = number
  description = "Memory allocation in MB (Playwright needs at least 1024MB)"
  default     = 1024
}

variable "name_prefix" {
  type        = string
  description = "Prefix for resource names (e.g., bluemoxon-staging)"
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}

variable "timeout" {
  type        = number
  description = "Function timeout in seconds (scraping can take time)"
  default     = 60
}

variable "provisioned_concurrency" {
  type        = number
  description = "Number of provisioned concurrent executions (0 to disable)"
  default     = 0
}
