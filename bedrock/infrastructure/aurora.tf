# Aurora PostgreSQL Serverless v2

# DB Subnet Group
resource "aws_db_subnet_group" "aurora" {
  name       = "${local.name_prefix}-aurora-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-aurora-subnet-group"
    }
  )
}

# DB Cluster Parameter Group
resource "aws_rds_cluster_parameter_group" "aurora" {
  name        = "${local.name_prefix}-aurora-cluster-pg"
  family      = "aurora-postgresql15"
  description = "Cluster parameter group for Aurora PostgreSQL 15"

  parameter {
    name  = "log_statement"
    value = "all"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-aurora-cluster-pg"
    }
  )
}

# DB Parameter Group (for instances)
resource "aws_db_parameter_group" "aurora" {
  name        = "${local.name_prefix}-aurora-pg"
  family      = "aurora-postgresql15"
  description = "Parameter group for Aurora PostgreSQL 15 instances"

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-aurora-pg"
    }
  )
}

# Aurora Cluster
resource "aws_rds_cluster" "aurora" {
  cluster_identifier = "${local.name_prefix}-aurora"
  engine             = "aurora-postgresql"
  engine_mode        = "provisioned"
  engine_version     = "15.4"
  database_name      = var.aurora_database_name
  master_username    = var.aurora_master_username
  master_password    = data.aws_secretsmanager_secret_version.aurora_password.secret_string

  db_subnet_group_name            = aws_db_subnet_group.aurora.name
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.aurora.name
  vpc_security_group_ids          = [aws_security_group.aurora.id]

  # Serverless v2 scaling configuration
  serverlessv2_scaling_configuration {
    min_capacity = var.aurora_min_capacity
    max_capacity = var.aurora_max_capacity
  }

  # Backup configuration
  backup_retention_period      = 7
  preferred_backup_window      = "03:00-04:00"
  preferred_maintenance_window = "sun:04:00-sun:05:00"

  # Encryption
  storage_encrypted = true
  kms_key_id        = aws_kms_key.aurora.arn

  # Deletion protection
  deletion_protection = false # Set to true in production
  skip_final_snapshot = true  # Set to false in production
  # final_snapshot_identifier = "${local.name_prefix}-aurora-final-snapshot"

  # CloudWatch Logs
  enabled_cloudwatch_logs_exports = ["postgresql"]

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-aurora-cluster"
    }
  )

  depends_on = [aws_cloudwatch_log_group.aurora]
}

# Aurora Cluster Instance (Serverless v2)
resource "aws_rds_cluster_instance" "aurora" {
  identifier              = "${local.name_prefix}-aurora-instance-1"
  cluster_identifier      = aws_rds_cluster.aurora.id
  instance_class          = "db.serverless"
  engine                  = aws_rds_cluster.aurora.engine
  engine_version          = aws_rds_cluster.aurora.engine_version
  db_parameter_group_name = aws_db_parameter_group.aurora.name

  # Performance Insights
  performance_insights_enabled    = true
  performance_insights_kms_key_id = aws_kms_key.aurora.arn
  performance_insights_retention_period = 7

  # Monitoring
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-aurora-instance-1"
    }
  )
}

# KMS Key for Aurora Encryption
resource "aws_kms_key" "aurora" {
  description             = "KMS key for Aurora PostgreSQL encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-aurora-kms"
    }
  )
}

resource "aws_kms_alias" "aurora" {
  name          = "alias/${local.name_prefix}-aurora"
  target_key_id = aws_kms_key.aurora.key_id
}

# CloudWatch Log Group for Aurora
resource "aws_cloudwatch_log_group" "aurora" {
  name              = "/aws/rds/cluster/${local.name_prefix}-aurora/postgresql"
  retention_in_days = 7

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-aurora-logs"
    }
  )
}

# IAM Role for Enhanced Monitoring
resource "aws_iam_role" "rds_monitoring" {
  name = "${local.name_prefix}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-rds-monitoring-role"
    }
  )
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}
