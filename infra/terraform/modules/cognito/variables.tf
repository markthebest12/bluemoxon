variable "access_token_validity" {
  type        = number
  description = "Access token validity in hours"
  default     = 1
}

variable "allow_admin_create_user_only" {
  type        = bool
  description = "Only allow admin to create users"
  default     = false
}

variable "invite_email_message" {
  type        = string
  description = "Email message template for user invitation"
  default     = null
}

variable "invite_email_subject" {
  type        = string
  description = "Email subject for user invitation"
  default     = "Your temporary password"
}

variable "callback_urls" {
  type        = list(string)
  description = "Callback URLs for OAuth"
  default     = []
}

variable "domain_prefix" {
  type        = string
  description = "Cognito domain prefix"
  default     = null
}

variable "enable_oauth" {
  type        = bool
  description = "Enable OAuth flows"
  default     = false
}

variable "id_token_validity" {
  type        = number
  description = "ID token validity in hours"
  default     = 1
}

variable "logout_urls" {
  type        = list(string)
  description = "Logout URLs for OAuth"
  default     = []
}

variable "mfa_configuration" {
  type        = string
  description = "MFA configuration: OFF, ON, or OPTIONAL"
  default     = "OFF"

  validation {
    condition     = contains(["OFF", "ON", "OPTIONAL"], var.mfa_configuration)
    error_message = "MFA configuration must be OFF, ON, or OPTIONAL."
  }
}

variable "mfa_totp_enabled" {
  type        = bool
  description = "Enable TOTP (software token) MFA"
  default     = false
}

variable "password_minimum_length" {
  type        = number
  description = "Minimum password length"
  default     = 8
}

variable "password_require_symbols" {
  type        = bool
  description = "Require symbols in password"
  default     = true
}

variable "refresh_token_validity" {
  type        = number
  description = "Refresh token validity in days"
  default     = 30
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}

variable "user_pool_client_name_override" {
  type        = string
  description = "Override the client name (defaults to user_pool_name-client)"
  default     = null
}

variable "user_pool_name" {
  type        = string
  description = "Name of the Cognito user pool"
}
