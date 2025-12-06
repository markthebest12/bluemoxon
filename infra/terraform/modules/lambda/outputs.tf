# =============================================================================
# Lambda Module Outputs
# =============================================================================

output "function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.this.arn
}

output "function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.this.function_name
}

output "invoke_arn" {
  description = "Invoke ARN for API Gateway integration"
  value       = aws_lambda_function.this.invoke_arn
}

output "role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_exec.arn
}

output "role_name" {
  description = "Name of the Lambda execution role"
  value       = aws_iam_role.lambda_exec.name
}

output "log_group_name" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.lambda.name
}

output "alias_arn" {
  description = "ARN of the Lambda alias (if provisioned concurrency is enabled)"
  value       = var.provisioned_concurrency > 0 ? aws_lambda_alias.live[0].arn : null
}

output "alias_invoke_arn" {
  description = "Invoke ARN of the Lambda alias (if provisioned concurrency is enabled)"
  value       = var.provisioned_concurrency > 0 ? aws_lambda_alias.live[0].invoke_arn : null
}
