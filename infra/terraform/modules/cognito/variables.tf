variable "access_token_validity" {
  type        = number
  description = "Access token validity in hours"
  default     = 1
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

variable "user_pool_name" {
  type        = string
  description = "Name of the Cognito user pool"
}
