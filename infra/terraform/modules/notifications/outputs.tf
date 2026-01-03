output "sns_topic_arn" {
  description = "ARN of the tracking SMS SNS topic"
  value       = aws_sns_topic.tracking_sms.arn
}

output "sns_topic_name" {
  description = "Name of the tracking SMS SNS topic"
  value       = aws_sns_topic.tracking_sms.name
}
