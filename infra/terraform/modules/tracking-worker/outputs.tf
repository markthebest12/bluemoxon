output "queue_url" {
  description = "SQS queue URL"
  value       = aws_sqs_queue.jobs.url
}

output "queue_arn" {
  description = "SQS queue ARN"
  value       = aws_sqs_queue.jobs.arn
}

output "dlq_url" {
  description = "DLQ URL"
  value       = aws_sqs_queue.dlq.url
}

output "dispatcher_function_name" {
  description = "Dispatcher Lambda function name"
  value       = aws_lambda_function.dispatcher.function_name
}

output "worker_function_name" {
  description = "Worker Lambda function name"
  value       = aws_lambda_function.worker.function_name
}
