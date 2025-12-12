# =============================================================================
# Scraper Lambda Module (Container-based)
# =============================================================================
# Creates a container-based Lambda function for Playwright scraping.
# Uses Docker/ECR instead of zip packages for browser automation support.
# =============================================================================

# -----------------------------------------------------------------------------
# ECR Repository
# -----------------------------------------------------------------------------

resource "aws_ecr_repository" "scraper" {
  name                 = "${var.name_prefix}-scraper"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = var.tags
}

resource "aws_ecr_lifecycle_policy" "scraper" {
  repository = aws_ecr_repository.scraper.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 5 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 5
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# Lambda Function (Container-based)
# -----------------------------------------------------------------------------

resource "aws_lambda_function" "scraper" {
  function_name = "${var.name_prefix}-scraper"
  role          = aws_iam_role.scraper_exec.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.scraper.repository_url}:${var.image_tag}"
  timeout       = var.timeout
  memory_size   = var.memory_size

  environment {
    variables = merge(
      {
        ENVIRONMENT = var.environment
      },
      var.environment_variables
    )
  }

  tracing_config {
    mode = "Active"
  }

  tags = var.tags

  depends_on = [aws_cloudwatch_log_group.scraper]

  # Image deployment is handled by CI/CD
  lifecycle {
    ignore_changes = [
      image_uri,
    ]
  }
}

# -----------------------------------------------------------------------------
# IAM Role for Lambda Execution
# -----------------------------------------------------------------------------

resource "aws_iam_role" "scraper_exec" {
  name = "${var.name_prefix}-scraper-exec-role"

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
  role       = aws_iam_role.scraper_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# X-Ray tracing
resource "aws_iam_role_policy_attachment" "lambda_xray" {
  role       = aws_iam_role.scraper_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# ECR pull access
resource "aws_iam_role_policy" "ecr_access" {
  name = "ecr-access"
  role = aws_iam_role.scraper_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
        Resource = aws_ecr_repository.scraper.arn
      },
      {
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Log Group
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "scraper" {
  name              = "/aws/lambda/${var.name_prefix}-scraper"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Lambda Permission (allow API Lambda to invoke scraper)
# -----------------------------------------------------------------------------

resource "aws_lambda_permission" "allow_api_invoke" {
  count         = var.api_lambda_role_arn != null ? 1 : 0
  statement_id  = "AllowAPILambdaInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scraper.function_name
  principal     = "lambda.amazonaws.com"
  source_arn    = var.api_lambda_role_arn
}

# Policy for API Lambda to invoke scraper
resource "aws_iam_role_policy" "api_invoke_scraper" {
  count = var.api_lambda_role_name != null ? 1 : 0
  name  = "invoke-scraper"
  role  = var.api_lambda_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = aws_lambda_function.scraper.arn
      }
    ]
  })
}
