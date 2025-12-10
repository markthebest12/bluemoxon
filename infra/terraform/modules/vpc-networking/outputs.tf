output "nat_gateway_id" {
  description = "ID of the NAT Gateway"
  value       = var.enable_nat_gateway ? aws_nat_gateway.this[0].id : null
}

output "nat_gateway_public_ip" {
  description = "Public IP of the NAT Gateway"
  value       = var.enable_nat_gateway ? aws_eip.nat[0].public_ip : null
}

output "private_route_table_id" {
  description = "ID of the private route table"
  value       = var.enable_nat_gateway ? aws_route_table.private[0].id : null
}

output "s3_endpoint_id" {
  description = "ID of the S3 Gateway VPC endpoint"
  value       = var.enable_vpc_endpoints ? aws_vpc_endpoint.s3[0].id : null
}

output "secretsmanager_endpoint_id" {
  description = "ID of the Secrets Manager Interface VPC endpoint"
  value       = var.enable_vpc_endpoints ? aws_vpc_endpoint.secretsmanager[0].id : null
}

output "vpc_endpoints_security_group_id" {
  description = "ID of the VPC endpoints security group"
  value       = var.enable_vpc_endpoints ? aws_security_group.vpc_endpoints[0].id : null
}

output "cognito_idp_endpoint_id" {
  description = "ID of the Cognito IDP Interface VPC endpoint"
  value       = var.enable_vpc_endpoints && var.enable_cognito_endpoint ? aws_vpc_endpoint.cognito_idp[0].id : null
}
