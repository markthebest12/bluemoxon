# =============================================================================
# Eval Runbook Worker Module Outputs
# =============================================================================

output "dlq_arn" {
  description = "ARN of the dead letter queue"
  value       = aws_sqs_queue.dlq.arn
}

output "dlq_url" {
  description = "URL of the dead letter queue"
  value       = aws_sqs_queue.dlq.url
}

output "function_arn" {
  description = "ARN of the worker Lambda function"
  value       = aws_lambda_function.worker.arn
}

output "function_name" {
  description = "Name of the worker Lambda function"
  value       = aws_lambda_function.worker.function_name
}

output "queue_arn" {
  description = "ARN of the SQS queue for eval runbook jobs"
  value       = aws_sqs_queue.jobs.arn
}

output "queue_name" {
  description = "Name of the SQS queue for eval runbook jobs"
  value       = aws_sqs_queue.jobs.name
}

output "queue_url" {
  description = "URL of the SQS queue for eval runbook jobs"
  value       = aws_sqs_queue.jobs.url
}

output "role_arn" {
  description = "ARN of the worker Lambda's IAM role"
  value       = aws_iam_role.worker_exec.arn
}

output "role_name" {
  description = "Name of the worker Lambda's IAM role"
  value       = aws_iam_role.worker_exec.name
}
