# =============================================================================
# Input Variables
# =============================================================================

# -----------------------------------------------------------------------------
# Required Variables
# -----------------------------------------------------------------------------

variable "secret_name" {
  type        = string
  description = "Name of the secret in Secrets Manager"
}

variable "secret_value" {
  type        = map(string)
  description = "Secret value as a map (will be stored as JSON)"
  sensitive   = true
}

# -----------------------------------------------------------------------------
# Optional Variables
# -----------------------------------------------------------------------------

variable "description" {
  type        = string
  description = "Description of the secret"
  default     = ""
}

variable "recovery_window_in_days" {
  type        = number
  description = "Number of days to wait before deleting the secret (0-30, 0 = immediate)"
  default     = 7
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}
