# SQS Queue for image processing jobs
resource "aws_sqs_queue" "jobs" {
  name                       = "${var.name_prefix}-image-processing"
  visibility_timeout_seconds = 360
  message_retention_seconds  = 345600
  receive_wait_time_seconds  = 20

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Environment = var.environment
    Service     = "image-processing"
  }
}

# Dead letter queue
resource "aws_sqs_queue" "dlq" {
  name                      = "${var.name_prefix}-image-processing-dlq"
  message_retention_seconds = 1209600

  tags = {
    Environment = var.environment
    Service     = "image-processing"
  }
}

# IAM role for Lambda
resource "aws_iam_role" "worker_exec" {
  name = "${var.name_prefix}-image-processor-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# CloudWatch Logs policy
resource "aws_iam_role_policy_attachment" "worker_logs" {
  role       = aws_iam_role.worker_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# VPC access policy (required when Lambda is in VPC)
resource "aws_iam_role_policy_attachment" "worker_vpc" {
  count      = length(var.vpc_subnet_ids) > 0 ? 1 : 0
  role       = aws_iam_role.worker_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# SQS policy
resource "aws_iam_role_policy" "worker_sqs" {
  name = "${var.name_prefix}-image-processor-sqs"
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

# S3 policy for images bucket
resource "aws_iam_role_policy" "worker_s3" {
  name = "${var.name_prefix}-image-processor-s3"
  role = aws_iam_role.worker_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "arn:aws:s3:::${var.images_bucket}/*"
      }
    ]
  })
}

# Secrets Manager policy
resource "aws_iam_role_policy" "worker_secrets" {
  name = "${var.name_prefix}-image-processor-secrets"
  role = aws_iam_role.worker_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "secretsmanager:GetSecretValue"
        Resource = var.database_secret_arn
      }
    ]
  })
}

# Lambda function
resource "aws_lambda_function" "worker" {
  function_name = "${var.name_prefix}-image-processor"
  role          = aws_iam_role.worker_exec.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = var.timeout
  memory_size   = var.memory_size

  s3_bucket = var.s3_bucket
  s3_key    = var.s3_key

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = merge({
      ENVIRONMENT           = var.environment
      BMX_IMAGES_BUCKET     = var.images_bucket
      BMX_IMAGES_CDN_DOMAIN = var.images_cdn_domain
      DB_SECRET_ARN         = var.database_secret_arn
    }, var.environment_variables)
  }

  dynamic "vpc_config" {
    for_each = length(var.vpc_subnet_ids) > 0 ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  tags = {
    Environment = var.environment
    Service     = "image-processing"
  }
}

# SQS trigger for Lambda
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn                   = aws_sqs_queue.jobs.arn
  function_name                      = aws_lambda_function.worker.arn
  batch_size                         = 1
  function_response_types            = ["ReportBatchItemFailures"]
  maximum_batching_window_in_seconds = 0
}

# CloudWatch alarm for DLQ messages
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  count               = var.alarm_sns_topic_arn != "" ? 1 : 0
  alarm_name          = "${var.name_prefix}-image-processing-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Image processing jobs failed and moved to DLQ"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.dlq.name
  }

  alarm_actions = [var.alarm_sns_topic_arn]
  ok_actions    = [var.alarm_sns_topic_arn]

  tags = {
    Environment = var.environment
    Service     = "image-processing"
  }
}

# IAM policy for API Lambda to send messages to image processing queue
resource "aws_iam_role_policy" "api_sqs_send" {
  count = var.api_lambda_role_name != null ? 1 : 0
  name  = "sqs-send-image-processing-jobs"
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
