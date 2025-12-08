# VPC Networking Module

Creates NAT Gateway infrastructure for Lambda functions that need outbound internet access from private subnets.

## When to Use

Use this module when:
- Lambda is in a VPC and needs to call external services (e.g., Cognito API)
- VPC endpoints are not available or incompatible (e.g., Cognito Managed Login)
- You need outbound internet access from private subnets

## Architecture

```
Internet Gateway (IGW)
       │
       ▼
┌──────────────────────────┐
│   Public Subnet          │
│   (NAT Gateway here)     │
└──────────────────────────┘
       │
       ▼ (NAT)
┌──────────────────────────┐
│   Private Subnets        │
│   (Lambda here)          │
│   Route: 0.0.0.0/0 → NAT │
└──────────────────────────┘
```

## Usage

```hcl
module "vpc_networking" {
  source = "./modules/vpc-networking"

  vpc_id             = data.aws_vpc.default.id
  name_prefix        = "myapp-staging"
  enable_nat_gateway = true
  public_subnet_id   = "subnet-abc123"    # Subnet with IGW route
  private_subnet_ids = [                   # Subnets for Lambda
    "subnet-def456",
    "subnet-ghi789"
  ]

  tags = {
    Environment = "staging"
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
| enable_nat_gateway | Enable NAT Gateway | `bool` | `false` | no |
| name_prefix | Prefix for resource names | `string` | n/a | yes |
| private_subnet_ids | Private subnet IDs for route table association | `list(string)` | `[]` | no |
| public_subnet_id | Public subnet ID for NAT Gateway placement | `string` | `null` | no |
| tags | Resource tags | `map(string)` | `{}` | no |
| vpc_id | VPC ID for the route table | `string` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| nat_gateway_id | ID of the NAT Gateway |
| nat_gateway_public_ip | Public IP of the NAT Gateway |
| private_route_table_id | ID of the private route table |

## Cost

NAT Gateway costs approximately $32/month (data transfer additional).
