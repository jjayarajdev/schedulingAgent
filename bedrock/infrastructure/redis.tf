# ElastiCache Redis

# Redis Subnet Group
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.name_prefix}-redis-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-redis-subnet-group"
    }
  )
}

# Redis Parameter Group
resource "aws_elasticache_parameter_group" "redis" {
  name   = "${local.name_prefix}-redis-pg"
  family = var.redis_parameter_group_family

  # Enable cluster mode for future scaling
  parameter {
    name  = "cluster-enabled"
    value = "no"
  }

  # Session timeout
  parameter {
    name  = "timeout"
    value = "300"
  }

  # Memory management
  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-redis-pg"
    }
  )
}

# Redis Cluster
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${local.name_prefix}-redis"
  engine               = "redis"
  engine_version       = "7.1"
  node_type            = var.redis_node_type
  num_cache_nodes      = var.redis_num_cache_nodes
  parameter_group_name = aws_elasticache_parameter_group.redis.name
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [aws_security_group.redis.id]

  # Port
  port = 6379

  # Maintenance window
  maintenance_window = "sun:05:00-sun:06:00"

  # Snapshot configuration
  snapshot_retention_limit = 5
  snapshot_window          = "03:00-04:00"

  # Notifications
  notification_topic_arn = aws_sns_topic.elasticache_notifications.arn

  # Logging
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_engine_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "engine-log"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-redis"
    }
  )

  depends_on = [
    aws_cloudwatch_log_group.redis_slow_log,
    aws_cloudwatch_log_group.redis_engine_log
  ]
}

# CloudWatch Log Groups for Redis
resource "aws_cloudwatch_log_group" "redis_slow_log" {
  name              = "/aws/elasticache/${local.name_prefix}-redis/slow-log"
  retention_in_days = 7

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-redis-slow-log"
    }
  )
}

resource "aws_cloudwatch_log_group" "redis_engine_log" {
  name              = "/aws/elasticache/${local.name_prefix}-redis/engine-log"
  retention_in_days = 7

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-redis-engine-log"
    }
  )
}

# SNS Topic for ElastiCache Notifications
resource "aws_sns_topic" "elasticache_notifications" {
  name = "${local.name_prefix}-elasticache-notifications"

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-elasticache-notifications"
    }
  )
}

# CloudWatch Alarms for Redis

# High CPU alarm
resource "aws_cloudwatch_metric_alarm" "redis_cpu_high" {
  alarm_name          = "${local.name_prefix}-redis-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = 75
  alarm_description   = "This metric monitors Redis CPU utilization"
  alarm_actions       = [aws_sns_topic.elasticache_notifications.arn]

  dimensions = {
    CacheClusterId = aws_elasticache_cluster.redis.id
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-redis-cpu-high"
    }
  )
}

# High memory alarm
resource "aws_cloudwatch_metric_alarm" "redis_memory_high" {
  alarm_name          = "${local.name_prefix}-redis-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "This metric monitors Redis memory utilization"
  alarm_actions       = [aws_sns_topic.elasticache_notifications.arn]

  dimensions = {
    CacheClusterId = aws_elasticache_cluster.redis.id
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-redis-memory-high"
    }
  )
}

# Evictions alarm
resource "aws_cloudwatch_metric_alarm" "redis_evictions" {
  alarm_name          = "${local.name_prefix}-redis-evictions"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Evictions"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Sum"
  threshold           = 100
  alarm_description   = "This metric monitors Redis evictions"
  alarm_actions       = [aws_sns_topic.elasticache_notifications.arn]

  dimensions = {
    CacheClusterId = aws_elasticache_cluster.redis.id
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-redis-evictions"
    }
  )
}
