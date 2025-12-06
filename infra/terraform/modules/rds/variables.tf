variable "allocated_storage" {
  type        = number
  description = "Allocated storage in GB"
  default     = 20
}

variable "allowed_security_groups" {
  type        = list(string)
  description = "Security groups allowed to access the database"
  default     = []
}

variable "backup_retention_period" {
  type        = number
  description = "Backup retention period in days"
  default     = 7
}

variable "backup_window" {
  type        = string
  description = "Preferred backup window"
  default     = "03:00-04:00"
}

variable "database_name" {
  type        = string
  description = "Name of the database to create"
}

variable "deletion_protection" {
  type        = bool
  description = "Enable deletion protection"
  default     = true
}

variable "engine_version" {
  type        = string
  description = "PostgreSQL engine version"
  default     = "16.3"
}

variable "identifier" {
  type        = string
  description = "RDS instance identifier"
}

variable "instance_class" {
  type        = string
  description = "RDS instance class"
  default     = "db.t3.micro"
}

variable "maintenance_window" {
  type        = string
  description = "Preferred maintenance window"
  default     = "sun:04:00-sun:05:00"
}

variable "master_password" {
  type        = string
  description = "Master password"
  sensitive   = true
}

variable "master_username" {
  type        = string
  description = "Master username"
  sensitive   = true
}

variable "max_allocated_storage" {
  type        = number
  description = "Maximum allocated storage for autoscaling"
  default     = 100
}

variable "performance_insights_enabled" {
  type        = bool
  description = "Enable Performance Insights"
  default     = false
}

variable "skip_final_snapshot" {
  type        = bool
  description = "Skip final snapshot on deletion"
  default     = false
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for the DB subnet group"
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for the RDS instance"
}
