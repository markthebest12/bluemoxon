output "ecr_repository_url" {
  description = "URL of the ECR repository for pushing images"
  value       = aws_ecr_repository.scraper.repository_url
}

output "ecr_repository_arn" {
  description = "ARN of the ECR repository"
  value       = aws_ecr_repository.scraper.arn
}

output "function_arn" {
  description = "ARN of the scraper Lambda function"
  value       = aws_lambda_function.scraper.arn
}

output "function_name" {
  description = "Name of the scraper Lambda function"
  value       = aws_lambda_function.scraper.function_name
}

output "invoke_arn" {
  description = "Invoke ARN of the scraper Lambda function"
  value       = aws_lambda_function.scraper.invoke_arn
}

output "log_group_name" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.scraper.name
}

output "role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.scraper_exec.arn
}

output "role_name" {
  description = "Name of the Lambda execution role"
  value       = aws_iam_role.scraper_exec.name
}
