# =============================================================================
# Notifications Module
# =============================================================================
# Creates notification infrastructure for carrier tracking:
# - SNS topic for SMS notifications
# - IAM policy for Lambda to publish to SNS
# - Optional SES permissions for email notifications
# =============================================================================

# -----------------------------------------------------------------------------
# SNS Topic for SMS Notifications
# -----------------------------------------------------------------------------

resource "aws_sns_topic" "tracking_sms" {
  name = "${var.name_prefix}-tracking-sms"

  tags = var.tags
}

# -----------------------------------------------------------------------------
# IAM Policy for Lambda SNS Access
# -----------------------------------------------------------------------------

resource "aws_iam_role_policy" "sns_publish" {
  count = var.lambda_role_name != null ? 1 : 0
  name  = "sns-publish-tracking"
  role  = var.lambda_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.tracking_sms.arn
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# IAM Policy for Lambda SES Access
# -----------------------------------------------------------------------------

resource "aws_iam_role_policy" "ses_send" {
  count = var.lambda_role_name != null && var.enable_ses ? 1 : 0
  name  = "ses-send-tracking"
  role  = var.lambda_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        # SES requires specific resource format or * for identity-based sending
        # Using * allows sending from any verified identity in the account
        Resource = "*"
        Condition = {
          StringEquals = {
            "ses:FromAddress" = var.ses_from_email
          }
        }
      }
    ]
  })
}
