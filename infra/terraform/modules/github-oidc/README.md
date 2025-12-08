# GitHub OIDC Module

Creates an OIDC provider and IAM role for GitHub Actions to deploy to AWS using
federated authentication (no static credentials).

## Resources Created

- `aws_iam_openid_connect_provider` - GitHub Actions OIDC provider
- `aws_iam_role` - IAM role assumable by GitHub Actions
- `aws_iam_role_policy` - Inline policy with deployment permissions

## Usage

```hcl
module "github_oidc" {
  source = "./modules/github-oidc"

  github_repo          = "owner/repository"
  lambda_function_arns = ["arn:aws:lambda:us-west-2:123456789012:function:my-app-*"]
  frontend_bucket_arns = ["arn:aws:s3:::my-frontend-bucket"]
  images_bucket_arns   = ["arn:aws:s3:::my-images-bucket"]
  cloudfront_distribution_arns = [
    "arn:aws:cloudfront::123456789012:distribution/XXXXXXXXXXXXX"
  ]

  tags = {
    Environment = "production"
  }
}
```

## Bootstrap Note

This module creates the OIDC provider and role that GitHub Actions uses to deploy
via Terraform. For initial setup (chicken-and-egg problem), these resources must
first be created manually or via a bootstrap script, then imported into Terraform.

### Import Commands

```bash
# Import OIDC provider
terraform import 'module.github_oidc.aws_iam_openid_connect_provider.github' \
  "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"

# Import IAM role
terraform import 'module.github_oidc.aws_iam_role.github_actions' \
  "github-actions-deploy"

# Import IAM policy
terraform import 'module.github_oidc.aws_iam_role_policy.deploy' \
  "github-actions-deploy:github-actions-deploy-policy"
```
