# infra/terraform/modules/lambda-layer/outputs.tf
output "layer_arn" {
  description = "ARN of the Lambda layer (without version)"
  value       = aws_lambda_layer_version.this.layer_arn
}

output "layer_version_arn" {
  description = "ARN of the Lambda layer version"
  value       = aws_lambda_layer_version.this.arn
}

output "layer_version" {
  description = "Version number of the layer"
  value       = aws_lambda_layer_version.this.version
}
