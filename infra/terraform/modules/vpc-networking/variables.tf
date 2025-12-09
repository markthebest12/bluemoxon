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

variable "enable_vpc_endpoints" {
  type        = bool
  description = "Enable VPC endpoints for S3 and Secrets Manager"
  default     = false
}

variable "create_lambda_sg_rule" {
  type        = bool
  description = "Whether to create the Lambda security group ingress rule"
  default     = false
}

variable "cognito_endpoint_subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for Cognito VPC endpoint (must be in AZs supported by Cognito: us-west-2a/b/c)"
  default     = []
}

variable "enable_cognito_endpoint" {
  type        = bool
  description = "Enable Cognito IDP Interface VPC endpoint (for Lambda to call Cognito APIs)"
  default     = true
}

variable "lambda_security_group_id" {
  type        = string
  description = "Lambda security group ID (for VPC endpoint ingress rules)"
  default     = null
}

variable "route_table_ids" {
  type        = list(string)
  description = "Route table IDs for S3 Gateway endpoint association"
  default     = []
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
