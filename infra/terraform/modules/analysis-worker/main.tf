# =============================================================================
# Analysis Worker Module
# =============================================================================
# Creates SQS queue + Lambda worker for async Bedrock analysis generation.
# Enables long-running analysis jobs that bypass API Gateway's 29s timeout.
# =============================================================================

# -----------------------------------------------------------------------------
# SQS Dead Letter Queue
# -----------------------------------------------------------------------------

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.name_prefix}-analysis-jobs-dlq"
  message_retention_seconds = 1209600 # 14 days

  tags = var.tags
}

# -----------------------------------------------------------------------------
# SQS Main Queue
# -----------------------------------------------------------------------------

resource "aws_sqs_queue" "jobs" {
  name                       = "${var.name_prefix}-analysis-jobs"
  visibility_timeout_seconds = var.visibility_timeout
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20     # Long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Lambda Function
# -----------------------------------------------------------------------------

resource "aws_lambda_function" "worker" {
  function_name = "${var.name_prefix}-analysis-worker"
  role          = aws_iam_role.worker_exec.arn
  handler       = var.handler
  runtime       = var.runtime
  memory_size   = var.memory_size
  timeout       = var.timeout

  s3_bucket = var.s3_bucket
  s3_key    = var.s3_key

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = merge(
      {
        ENVIRONMENT = var.environment
      },
      var.environment_variables
    )
  }

  dynamic "vpc_config" {
    for_each = length(var.subnet_ids) > 0 ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = var.security_group_ids
    }
  }

  tracing_config {
    mode = "Active"
  }

  tags = var.tags

  depends_on = [aws_cloudwatch_log_group.worker]

  # Code deployment is handled by CI/CD
  # Layers are managed by CI/CD workflow, not Terraform
  lifecycle {
    ignore_changes = [
      s3_key,
      layers,
    ]
  }
}

# -----------------------------------------------------------------------------
# SQS Event Source Mapping
# -----------------------------------------------------------------------------

resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.jobs.arn
  function_name    = aws_lambda_function.worker.arn
  batch_size       = 1 # Process one job at a time

  # Only succeed if function completes successfully
  function_response_types = ["ReportBatchItemFailures"]
}

# -----------------------------------------------------------------------------
# IAM Role for Lambda Execution
# -----------------------------------------------------------------------------

resource "aws_iam_role" "worker_exec" {
  name = "${var.name_prefix}-analysis-worker-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# Basic Lambda execution (CloudWatch Logs)
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.worker_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# VPC access (ENI management)
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  count      = length(var.subnet_ids) > 0 ? 1 : 0
  role       = aws_iam_role.worker_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# X-Ray tracing
resource "aws_iam_role_policy_attachment" "lambda_xray" {
  role       = aws_iam_role.worker_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# SQS access (receive + delete messages)
resource "aws_iam_role_policy" "sqs_access" {
  name = "sqs-access"
  role = aws_iam_role.worker_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.jobs.arn
      }
    ]
  })
}

# Secrets Manager access
resource "aws_iam_role_policy" "secrets_access" {
  count = length(var.secrets_arns) > 0 ? 1 : 0
  name  = "secrets-access"
  role  = aws_iam_role.worker_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = var.secrets_arns
      }
    ]
  })
}

# S3 access for images bucket
resource "aws_iam_role_policy" "s3_access" {
  count = length(var.s3_bucket_arns) > 0 ? 1 : 0
  name  = "s3-access"
  role  = aws_iam_role.worker_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = concat(
          var.s3_bucket_arns,
          [for arn in var.s3_bucket_arns : "${arn}/*"]
        )
      }
    ]
  })
}

# Bedrock access for AI-powered analysis generation
# Supports both foundation models and cross-region inference profiles
resource "aws_iam_role_policy" "bedrock_access" {
  count = length(var.bedrock_model_ids) > 0 ? 1 : 0
  name  = "bedrock-access"
  role  = aws_iam_role.worker_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = concat(
          # Foundation models (direct invocation)
          [for model_id in var.bedrock_model_ids : "arn:aws:bedrock:*::foundation-model/${model_id}"],
          # Cross-region inference profiles (us.anthropic.* format)
          ["arn:aws:bedrock:*:*:inference-profile/us.anthropic.*"]
        )
      },
      {
        # Required for Opus 4.5 model access verification at runtime
        # Without these, InvokeModel fails with AccessDeniedException
        Effect = "Allow"
        Action = [
          "aws-marketplace:ViewSubscriptions",
          "aws-marketplace:Subscribe"
        ]
        Resource = "*"
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Log Group
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/lambda/${var.name_prefix}-analysis-worker"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# -----------------------------------------------------------------------------
# IAM Policy for API Lambda to send messages to SQS
# -----------------------------------------------------------------------------

resource "aws_iam_role_policy" "api_sqs_send" {
  count = var.api_lambda_role_name != null ? 1 : 0
  name  = "sqs-send-analysis-jobs"
  role  = var.api_lambda_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueUrl",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.jobs.arn
      }
    ]
  })
}
