variable "api_name" {
  type        = string
  description = "Name of the API Gateway"
}

variable "certificate_arn" {
  type        = string
  description = "ACM certificate ARN for custom domain"
  default     = null
}

variable "cors_allow_credentials" {
  type        = bool
  description = "Allow credentials in CORS"
  default     = false
}

variable "cors_allowed_headers" {
  type        = list(string)
  description = "Allowed headers for CORS"
  default     = ["*"]
}

variable "cors_allowed_methods" {
  type        = list(string)
  description = "Allowed methods for CORS"
  default     = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
}

variable "cors_allowed_origins" {
  type        = list(string)
  description = "Allowed origins for CORS"
  default     = ["*"]
}

variable "cors_expose_headers" {
  type        = list(string)
  description = "Headers to expose in CORS response. Must match backend/app/main.py CORS_EXPOSE_HEADERS."
  # Order matches backend: X-App-Version, X-Environment, X-Cold-Start
  # Note: This only affects staging until prod API Gateway is managed by Terraform
  default     = ["X-App-Version", "X-Environment", "X-Cold-Start"]
}

variable "cors_max_age" {
  type        = number
  description = "Max age for CORS preflight cache"
  default     = 3600
}

variable "domain_name" {
  type        = string
  description = "Custom domain name for the API"
  default     = null
}

variable "lambda_function_name" {
  type        = string
  description = "Lambda function name for permission"
}

variable "lambda_invoke_arn" {
  type        = string
  description = "Lambda function invoke ARN"
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention in days"
  default     = 14
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}
