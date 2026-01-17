output "queue_url" {
  description = "SQS queue URL"
  value       = aws_sqs_queue.jobs.url
}

output "queue_arn" {
  description = "SQS queue ARN"
  value       = aws_sqs_queue.jobs.arn
}

output "queue_name" {
  description = "SQS queue name"
  value       = aws_sqs_queue.jobs.name
}

output "dlq_url" {
  description = "Dead letter queue URL"
  value       = aws_sqs_queue.dlq.url
}

output "function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.worker.function_name
}

output "function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.worker.arn
}

output "role_name" {
  description = "Lambda execution role name"
  value       = aws_iam_role.worker_exec.name
}
