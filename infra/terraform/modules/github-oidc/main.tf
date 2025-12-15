# =============================================================================
# GitHub Actions OIDC Module
# =============================================================================
# Creates OIDC provider and IAM role for GitHub Actions to deploy to AWS.
# =============================================================================

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# -----------------------------------------------------------------------------
# OIDC Provider
# -----------------------------------------------------------------------------

resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = ["sts.amazonaws.com"]

  # GitHub's OIDC thumbprint
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]

  tags = var.tags
}

# -----------------------------------------------------------------------------
# IAM Role
# -----------------------------------------------------------------------------

resource "aws_iam_role" "github_actions" {
  name = var.role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:*"
          }
        }
      }
    ]
  })

  tags = var.tags
}

# -----------------------------------------------------------------------------
# IAM Policy
# -----------------------------------------------------------------------------

resource "aws_iam_role_policy" "deploy" {
  name = var.policy_name
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      # Lambda deployment permissions
      [
        {
          Sid    = "LambdaDeployment"
          Effect = "Allow"
          Action = [
            "lambda:UpdateFunctionCode",
            "lambda:GetFunction",
            "lambda:GetFunctionConfiguration",
            "lambda:PublishVersion",
            "lambda:UpdateAlias",
            "lambda:CreateAlias",
            "lambda:GetAlias",
            "lambda:ListVersionsByFunction",
            "lambda:DeleteFunction"
          ]
          Resource = var.lambda_function_arns
        }
      ],
      # S3 Frontend deployment permissions
      length(var.frontend_bucket_arns) > 0 ? [
        {
          Sid    = "S3FrontendDeployment"
          Effect = "Allow"
          Action = [
            "s3:PutObject",
            "s3:GetObject",
            "s3:DeleteObject",
            "s3:ListBucket"
          ]
          Resource = concat(
            var.frontend_bucket_arns,
            [for arn in var.frontend_bucket_arns : "${arn}/*"]
          )
        }
      ] : [],
      # S3 Images access permissions
      length(var.images_bucket_arns) > 0 ? [
        {
          Sid    = "S3ImagesAccess"
          Effect = "Allow"
          Action = [
            "s3:GetObject",
            "s3:PutObject",
            "s3:ListBucket"
          ]
          Resource = concat(
            var.images_bucket_arns,
            [for arn in var.images_bucket_arns : "${arn}/*"]
          )
        }
      ] : [],
      # CloudFront invalidation permissions
      length(var.cloudfront_distribution_arns) > 0 ? [
        {
          Sid    = "CloudFrontInvalidation"
          Effect = "Allow"
          Action = [
            "cloudfront:CreateInvalidation",
            "cloudfront:GetInvalidation"
          ]
          Resource = var.cloudfront_distribution_arns
        }
      ] : [],
      # ECR permissions for Docker image deployment
      length(var.ecr_repository_arns) > 0 ? [
        {
          Sid    = "ECRAuth"
          Effect = "Allow"
          Action = [
            "ecr:GetAuthorizationToken"
          ]
          Resource = "*"
        },
        {
          Sid    = "ECRPushPull"
          Effect = "Allow"
          Action = [
            "ecr:BatchCheckLayerAvailability",
            "ecr:GetDownloadUrlForLayer",
            "ecr:BatchGetImage",
            "ecr:PutImage",
            "ecr:InitiateLayerUpload",
            "ecr:UploadLayerPart",
            "ecr:CompleteLayerUpload",
            "ecr:DescribeRepositories",
            "ecr:DescribeImages"
          ]
          Resource = var.ecr_repository_arns
        }
      ] : [],
      # Terraform state access (cross-account for staging/prod state reading)
      var.terraform_state_bucket_arn != null ? [
        {
          Sid    = "TerraformStateAccess"
          Effect = "Allow"
          Action = [
            "s3:GetObject",
            "s3:ListBucket"
          ]
          Resource = [
            var.terraform_state_bucket_arn,
            "${var.terraform_state_bucket_arn}/*"
          ]
        }
      ] : [],
      var.terraform_state_dynamodb_table_arn != null ? [
        {
          Sid    = "DynamoDBLockAccess"
          Effect = "Allow"
          Action = [
            "dynamodb:GetItem",
            "dynamodb:PutItem",
            "dynamodb:DeleteItem"
          ]
          Resource = var.terraform_state_dynamodb_table_arn
        }
      ] : []
    )
  })
}
