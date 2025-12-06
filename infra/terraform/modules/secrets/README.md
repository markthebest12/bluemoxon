# Secrets Manager Module

Manages AWS Secrets Manager secrets for secure credential storage.

## Usage

```hcl
module "database_secret" {
  source = "./modules/secrets"

  secret_name = "bluemoxon-staging-db"
  description = "Database credentials for staging environment"

  secret_value = {
    username = "dbadmin"
    password = var.db_password
    host     = module.database.address
    port     = "5432"
    dbname   = "bluemoxon"
  }

  tags = local.common_tags
}
```

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.0 |
| aws | >= 5.0 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| secret_name | Name of the secret | `string` | n/a | yes |
| secret_value | Secret key-value pairs to store | `map(string)` | n/a | yes |
| description | Description of the secret | `string` | `""` | no |
| recovery_window_in_days | Days before permanent deletion | `number` | `7` | no |
| tags | Resource tags | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| arn | ARN of the secret |
| id | ID of the secret |
| name | Name of the secret |
