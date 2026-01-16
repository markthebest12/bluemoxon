# =============================================================================
# Tracking Worker Module
# =============================================================================
# Creates SQS queue + dispatcher + worker Lambdas for async tracking updates.
# EventBridge → Dispatcher → SQS → Worker
# =============================================================================

# -----------------------------------------------------------------------------
# SQS Dead Letter Queue
# -----------------------------------------------------------------------------

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.name_prefix}-tracking-jobs-dlq"
  message_retention_seconds = 1209600 # 14 days

  tags = var.tags
}

# -----------------------------------------------------------------------------
# SQS Main Queue
# -----------------------------------------------------------------------------

resource "aws_sqs_queue" "jobs" {
  name                       = "${var.name_prefix}-tracking-jobs"
  visibility_timeout_seconds = var.timeout_worker * 2
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20     # Long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })

  tags = var.tags
}

# -----------------------------------------------------------------------------
# IAM Role - Dispatcher
# -----------------------------------------------------------------------------

resource "aws_iam_role" "dispatcher" {
  name = "${var.name_prefix}-tracking-dispatcher-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "dispatcher_basic" {
  role       = aws_iam_role.dispatcher.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "dispatcher_vpc" {
  count      = length(var.subnet_ids) > 0 ? 1 : 0
  role       = aws_iam_role.dispatcher.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "dispatcher_sqs" {
  name = "sqs-send"
  role = aws_iam_role.dispatcher.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["sqs:SendMessage"]
      Resource = aws_sqs_queue.jobs.arn
    }]
  })
}

resource "aws_iam_role_policy" "dispatcher_secrets" {
  count = length(var.secrets_arns) > 0 ? 1 : 0
  name  = "secrets-access"
  role  = aws_iam_role.dispatcher.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = var.secrets_arns
    }]
  })
}

# -----------------------------------------------------------------------------
# IAM Role - Worker
# -----------------------------------------------------------------------------

resource "aws_iam_role" "worker" {
  name = "${var.name_prefix}-tracking-worker-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "worker_basic" {
  role       = aws_iam_role.worker.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "worker_vpc" {
  count      = length(var.subnet_ids) > 0 ? 1 : 0
  role       = aws_iam_role.worker.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "worker_sqs" {
  name = "sqs-receive"
  role = aws_iam_role.worker.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ]
      Resource = aws_sqs_queue.jobs.arn
    }]
  })
}

resource "aws_iam_role_policy" "worker_secrets" {
  count = length(var.secrets_arns) > 0 ? 1 : 0
  name  = "secrets-access"
  role  = aws_iam_role.worker.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = var.secrets_arns
    }]
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Log Groups
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "dispatcher" {
  name              = "/aws/lambda/${var.name_prefix}-tracking-dispatcher"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/lambda/${var.name_prefix}-tracking-worker"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Lambda - Dispatcher
# -----------------------------------------------------------------------------

resource "aws_lambda_function" "dispatcher" {
  function_name = "${var.name_prefix}-tracking-dispatcher"
  role          = aws_iam_role.dispatcher.arn
  handler       = var.handler_dispatcher
  runtime       = var.runtime
  memory_size   = var.memory_size_dispatcher
  timeout       = var.timeout_dispatcher

  s3_bucket = var.s3_bucket
  s3_key    = var.s3_key

  environment {
    variables = merge(
      { ENVIRONMENT = var.environment, TRACKING_QUEUE_URL = aws_sqs_queue.jobs.url },
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

  tags = var.tags

  depends_on = [aws_cloudwatch_log_group.dispatcher]

  lifecycle {
    ignore_changes = [
      s3_key,
      layers,
    ]
  }
}

# -----------------------------------------------------------------------------
# Lambda - Worker
# -----------------------------------------------------------------------------

resource "aws_lambda_function" "worker" {
  function_name = "${var.name_prefix}-tracking-worker"
  role          = aws_iam_role.worker.arn
  handler       = var.handler_worker
  runtime       = var.runtime
  memory_size   = var.memory_size_worker
  timeout       = var.timeout_worker

  s3_bucket = var.s3_bucket
  s3_key    = var.s3_key

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = merge(
      { ENVIRONMENT = var.environment },
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

  tags = var.tags

  depends_on = [aws_cloudwatch_log_group.worker]

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
  batch_size       = 1

  function_response_types = ["ReportBatchItemFailures"]
}

# -----------------------------------------------------------------------------
# EventBridge Schedule → Dispatcher
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_event_rule" "schedule" {
  name                = "${var.name_prefix}-tracking-schedule"
  description         = "Hourly tracking poll"
  schedule_expression = var.schedule_expression

  tags = var.tags
}

resource "aws_cloudwatch_event_target" "dispatcher" {
  rule      = aws_cloudwatch_event_rule.schedule.name
  target_id = "tracking-dispatcher"
  arn       = aws_lambda_function.dispatcher.arn
}

resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dispatcher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule.arn
}
