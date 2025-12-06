output "api_endpoint" {
  description = "Default endpoint URL of the API"
  value       = aws_apigatewayv2_api.this.api_endpoint
}

output "api_id" {
  description = "ID of the API Gateway"
  value       = aws_apigatewayv2_api.this.id
}

output "custom_domain_name" {
  description = "Custom domain name (if configured)"
  value       = try(aws_apigatewayv2_domain_name.this[0].domain_name, null)
}

output "custom_domain_target" {
  description = "Target domain for DNS CNAME record"
  value       = try(aws_apigatewayv2_domain_name.this[0].domain_name_configuration[0].target_domain_name, null)
}

output "execution_arn" {
  description = "Execution ARN for Lambda permissions"
  value       = aws_apigatewayv2_api.this.execution_arn
}

output "log_group_name" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.api.name
}
