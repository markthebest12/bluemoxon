# RDS Module

Creates a PostgreSQL RDS instance with security group, subnet group, automated backups, and optional Performance Insights.

## Usage

```hcl
module "database" {
  source = "./modules/rds"

  identifier      = "my-app-db"
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnet_ids
  database_name   = "myapp"
  master_username = var.db_username
  master_password = var.db_password

  instance_class    = "db.t3.small"
  allocated_storage = 50

  allowed_security_groups = [module.lambda.security_group_id]

  tags = {
    Environment = "production"
  }
}
```

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.6.0 |
| aws | ~> 5.0 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| allocated_storage | Allocated storage in GB | `number` | `20` | no |
| allowed_security_groups | Security groups allowed to access the database | `list(string)` | `[]` | no |
| backup_retention_period | Backup retention period in days | `number` | `7` | no |
| backup_window | Preferred backup window | `string` | `"03:00-04:00"` | no |
| database_name | Name of the database to create | `string` | n/a | yes |
| deletion_protection | Enable deletion protection | `bool` | `true` | no |
| engine_version | PostgreSQL engine version | `string` | `"16.3"` | no |
| identifier | RDS instance identifier | `string` | n/a | yes |
| instance_class | RDS instance class | `string` | `"db.t3.micro"` | no |
| maintenance_window | Preferred maintenance window | `string` | `"sun:04:00-sun:05:00"` | no |
| master_password | Master password | `string` | n/a | yes |
| master_username | Master username | `string` | n/a | yes |
| max_allocated_storage | Maximum allocated storage for autoscaling | `number` | `100` | no |
| performance_insights_enabled | Enable Performance Insights | `bool` | `false` | no |
| skip_final_snapshot | Skip final snapshot on deletion | `bool` | `false` | no |
| subnet_ids | Subnet IDs for the DB subnet group | `list(string)` | n/a | yes |
| tags | Resource tags | `map(string)` | `{}` | no |
| vpc_id | VPC ID for the RDS instance | `string` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| address | RDS instance address (hostname) |
| arn | RDS instance ARN |
| database_name | Name of the database |
| endpoint | RDS instance endpoint |
| instance_id | RDS instance ID |
| port | RDS instance port |
| security_group_id | Security group ID for the RDS instance |
