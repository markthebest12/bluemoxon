# =============================================================================
# Required Variables
# =============================================================================

variable "user_pool_name" {
  description = "Name of the Cognito user pool"
  type        = string
}

# =============================================================================
# Optional Variables
# =============================================================================

variable "password_minimum_length" {
  description = "Minimum password length"
  type        = number
  default     = 8
}

variable "password_require_symbols" {
  description = "Require symbols in password"
  type        = bool
  default     = true
}

variable "callback_urls" {
  description = "Callback URLs for OAuth"
  type        = list(string)
  default     = []
}

variable "logout_urls" {
  description = "Logout URLs for OAuth"
  type        = list(string)
  default     = []
}

variable "enable_oauth" {
  description = "Enable OAuth flows"
  type        = bool
  default     = false
}

variable "domain_prefix" {
  description = "Cognito domain prefix"
  type        = string
  default     = null
}

variable "access_token_validity" {
  description = "Access token validity in hours"
  type        = number
  default     = 1
}

variable "id_token_validity" {
  description = "ID token validity in hours"
  type        = number
  default     = 1
}

variable "refresh_token_validity" {
  description = "Refresh token validity in days"
  type        = number
  default     = 30
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
