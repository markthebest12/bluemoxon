variable "enable_nat_gateway" {
  type        = bool
  description = "Enable NAT Gateway for outbound internet access from private subnets"
  default     = false
}

variable "name_prefix" {
  type        = string
  description = "Prefix for resource names"
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs to associate with the NAT Gateway route table"
  default     = []
}

variable "public_subnet_id" {
  type        = string
  description = "Public subnet ID where the NAT Gateway will be placed (must have IGW route)"
  default     = null
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for the route table"
}
