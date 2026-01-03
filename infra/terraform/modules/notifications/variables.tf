variable "name_prefix" {
  type        = string
  description = "Resource name prefix (e.g., bluemoxon-staging)"
}

variable "lambda_role_name" {
  type        = string
  description = "Name of the Lambda IAM role to attach SNS/SES permissions to"
  default     = null
}

variable "enable_ses" {
  type        = bool
  description = "Enable SES email permissions for Lambda"
  default     = true
}

variable "ses_from_email" {
  type        = string
  description = "Verified SES email address for sending notifications"
  default     = "notifications@bluemoxon.com"
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}
