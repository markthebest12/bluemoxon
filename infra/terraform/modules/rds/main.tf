# =============================================================================
# RDS PostgreSQL Module
# =============================================================================
# Creates an RDS PostgreSQL instance with security group and subnet group.
# =============================================================================

# -----------------------------------------------------------------------------
# DB Subnet Group
# -----------------------------------------------------------------------------

resource "aws_db_subnet_group" "this" {
  name       = "${var.identifier}-subnet-group"
  subnet_ids = var.subnet_ids

  tags = merge(var.tags, {
    Name = "${var.identifier}-subnet-group"
  })
}

# -----------------------------------------------------------------------------
# Security Group
# -----------------------------------------------------------------------------

resource "aws_security_group" "this" {
  name        = "${var.identifier}-sg"
  description = "Security group for RDS instance ${var.identifier}"
  vpc_id      = var.vpc_id

  tags = merge(var.tags, {
    Name = "${var.identifier}-sg"
  })
}

resource "aws_vpc_security_group_ingress_rule" "postgres" {
  security_group_id = aws_security_group.this.id
  description       = "PostgreSQL from allowed security groups"

  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  referenced_security_group_id = var.allowed_security_group_id
}

resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.this.id
  description       = "Allow all outbound traffic"

  ip_protocol = "-1"
  cidr_ipv4   = "0.0.0.0/0"
}

# -----------------------------------------------------------------------------
# RDS Instance
# -----------------------------------------------------------------------------

resource "aws_db_instance" "this" {
  identifier = var.identifier

  # Engine
  engine         = "postgres"
  engine_version = var.engine_version

  # Instance
  instance_class = var.instance_class

  # Storage
  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  # Database
  db_name  = var.database_name
  username = var.master_username
  password = var.master_password

  # Network
  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.this.id]
  publicly_accessible    = var.publicly_accessible
  port                   = 5432

  # Backup
  backup_retention_period = var.backup_retention_period
  backup_window           = var.backup_window

  # Maintenance
  maintenance_window         = var.maintenance_window
  auto_minor_version_upgrade = true

  # Deletion
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${var.identifier}-final-${formatdate("YYYYMMDD-hhmmss", timestamp())}"
  deletion_protection       = var.deletion_protection

  # Monitoring
  performance_insights_enabled = var.performance_insights_enabled
  monitoring_interval          = var.monitoring_interval

  # Logs
  enabled_cloudwatch_logs_exports = var.enabled_cloudwatch_logs_exports

  # Parameter group
  parameter_group_name = var.parameter_group_name

  tags = var.tags

  lifecycle {
    ignore_changes = [
      final_snapshot_identifier
    ]
  }
}
