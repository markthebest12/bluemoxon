# =============================================================================
# Required Variables
# =============================================================================

variable "api_name" {
  description = "Name of the API Gateway"
  type        = string
}

variable "lambda_invoke_arn" {
  description = "Lambda function invoke ARN"
  type        = string
}

variable "lambda_function_name" {
  description = "Lambda function name for permission"
  type        = string
}

# =============================================================================
# Optional Variables
# =============================================================================

variable "domain_name" {
  description = "Custom domain name for the API"
  type        = string
  default     = null
}

variable "certificate_arn" {
  description = "ACM certificate ARN for custom domain"
  type        = string
  default     = null
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 14
}

# =============================================================================
# CORS Configuration
# =============================================================================

variable "cors_allowed_origins" {
  description = "Allowed origins for CORS"
  type        = list(string)
  default     = ["*"]
}

variable "cors_allowed_methods" {
  description = "Allowed methods for CORS"
  type        = list(string)
  default     = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
}

variable "cors_allowed_headers" {
  description = "Allowed headers for CORS"
  type        = list(string)
  default     = ["*"]
}

variable "cors_expose_headers" {
  description = "Headers to expose in CORS response"
  type        = list(string)
  default     = ["x-app-version", "x-environment"]
}

variable "cors_allow_credentials" {
  description = "Allow credentials in CORS"
  type        = bool
  default     = false
}

variable "cors_max_age" {
  description = "Max age for CORS preflight cache"
  type        = number
  default     = 3600
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
