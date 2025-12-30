# infra/terraform/modules/lambda-layer/main.tf
resource "aws_lambda_layer_version" "this" {
  layer_name          = var.layer_name
  description         = var.description
  compatible_runtimes = var.compatible_runtimes
  s3_bucket           = var.s3_bucket
  s3_key              = var.s3_key

  lifecycle {
    # Layer versions are immutable - CI/CD publishes new versions
    ignore_changes = [s3_key]
  }
}
