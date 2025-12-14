# =============================================================================
# Lambda Function Module
# =============================================================================
# Creates a Lambda function with IAM role, CloudWatch logs, and optional VPC.
# =============================================================================

# -----------------------------------------------------------------------------
# Security Group (optional - for VPC-enabled Lambda)
# -----------------------------------------------------------------------------

resource "aws_security_group" "lambda" {
  count = var.create_security_group && var.vpc_id != null ? 1 : 0

  name        = coalesce(var.security_group_name, "${var.function_name}-sg")
  description = coalesce(var.security_group_description, "Security group for Lambda function ${var.function_name}")
  vpc_id      = var.vpc_id

  tags = merge(var.tags, {
    Name = coalesce(var.security_group_name, "${var.function_name}-sg")
  })
}

resource "aws_vpc_security_group_egress_rule" "lambda_all" {
  count = var.create_security_group && var.vpc_id != null ? 1 : 0

  security_group_id = aws_security_group.lambda[0].id
  description       = "Allow all outbound traffic"

  ip_protocol = "-1"
  cidr_ipv4   = "0.0.0.0/0"
}

# -----------------------------------------------------------------------------
# Lambda Function
# -----------------------------------------------------------------------------

resource "aws_lambda_function" "this" {
  function_name = var.function_name
  role          = aws_iam_role.lambda_exec.arn
  handler       = var.handler
  runtime       = var.runtime
  memory_size   = var.memory_size
  timeout       = var.timeout

  filename         = var.package_path
  source_code_hash = var.source_code_hash

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
      subnet_ids = var.subnet_ids
      security_group_ids = concat(
        var.create_security_group && var.vpc_id != null ? [aws_security_group.lambda[0].id] : [],
        var.security_group_ids
      )
    }
  }

  tracing_config {
    mode = "Active"
  }

  tags = var.tags

  depends_on = [aws_cloudwatch_log_group.lambda]

  # Code deployment is handled by the deploy workflow (CI/CD)
  # Terraform manages infrastructure; workflow updates code via AWS CLI
  lifecycle {
    ignore_changes = [
      filename,
      source_code_hash,
    ]
  }
}

# -----------------------------------------------------------------------------
# IAM Role for Lambda Execution
# -----------------------------------------------------------------------------

resource "aws_iam_role" "lambda_exec" {
  name = coalesce(var.iam_role_name, "${var.function_name}-exec-role")

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
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# VPC access (ENI management)
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  count      = length(var.subnet_ids) > 0 ? 1 : 0
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# X-Ray tracing
resource "aws_iam_role_policy_attachment" "lambda_xray" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Secrets Manager access
resource "aws_iam_role_policy" "secrets_access" {
  count = length(var.secrets_arns) > 0 ? 1 : 0
  name  = "secrets-access"
  role  = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = var.secrets_arns
      }
    ]
  })
}

# S3 access for images bucket
resource "aws_iam_role_policy" "s3_access" {
  count = length(var.s3_bucket_arns) > 0 ? 1 : 0
  name  = "s3-access"
  role  = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
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

# Cognito access for user management
resource "aws_iam_role_policy" "cognito_access" {
  count = length(var.cognito_user_pool_arns) > 0 ? 1 : 0
  name  = "cognito-access"
  role  = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cognito-idp:AdminCreateUser",
          "cognito-idp:AdminDeleteUser",
          "cognito-idp:AdminDisableUser",
          "cognito-idp:AdminEnableUser",
          "cognito-idp:AdminGetUser",
          "cognito-idp:AdminInitiateAuth",
          "cognito-idp:AdminListGroupsForUser",
          "cognito-idp:AdminRemoveUserFromGroup",
          "cognito-idp:AdminResetUserPassword",
          "cognito-idp:AdminSetUserMFAPreference",
          "cognito-idp:AdminSetUserPassword",
          "cognito-idp:AdminUpdateUserAttributes",
          "cognito-idp:DescribeUserPool",
          "cognito-idp:GetUser",
          "cognito-idp:GetUserPoolMfaConfig",
          "cognito-idp:ListUsers"
        ]
        Resource = var.cognito_user_pool_arns
      }
    ]
  })
}

# Bedrock access for AI-powered analysis generation
resource "aws_iam_role_policy" "bedrock_access" {
  count = length(var.bedrock_model_ids) > 0 ? 1 : 0
  name  = "bedrock-access"
  role  = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [for model_id in var.bedrock_model_ids : "arn:aws:bedrock:*::foundation-model/${model_id}"]
      }
    ]
  })
}

# Lambda invoke access (e.g., for invoking scraper Lambda)
resource "aws_iam_role_policy" "lambda_invoke" {
  count = length(var.lambda_invoke_arns) > 0 ? 1 : 0
  name  = "lambda-invoke"
  role  = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = var.lambda_invoke_arns
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Log Group
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Provisioned Concurrency (optional - for warm starts in production)
# -----------------------------------------------------------------------------

resource "aws_lambda_alias" "live" {
  count            = var.provisioned_concurrency > 0 ? 1 : 0
  name             = var.environment
  function_name    = aws_lambda_function.this.function_name
  function_version = aws_lambda_function.this.version

  lifecycle {
    ignore_changes = [function_version]
  }
}

resource "aws_lambda_provisioned_concurrency_config" "this" {
  count                             = var.provisioned_concurrency > 0 ? 1 : 0
  function_name                     = aws_lambda_function.this.function_name
  qualifier                         = aws_lambda_alias.live[0].name
  provisioned_concurrent_executions = var.provisioned_concurrency
}
