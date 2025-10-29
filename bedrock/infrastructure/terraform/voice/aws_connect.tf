# ============================================================================
# AWS Connect Instance for Voice Integration (Phase 3)
# ============================================================================

# Variables for configuration
variable "connect_phone_number" {
  description = "Phone number to associate with AWS Connect (format: +1XXXXXXXXXX)"
  type        = string
  default     = "+18005551234"  # Placeholder - will be replaced with actual number
}

variable "connect_instance_alias" {
  description = "Unique alias for AWS Connect instance"
  type        = string
  default     = "pf-voice-dev"
}

# ============================================================================
# AWS Connect Instance
# ============================================================================

resource "aws_connect_instance" "main" {
  identity_management_type = "CONNECT_MANAGED"
  instance_alias           = "${var.prefix}-${var.connect_instance_alias}"

  inbound_calls_enabled  = true
  outbound_calls_enabled = false  # Phase 3 is inbound only

  # Contact flow logs
  contact_flow_logs_enabled = true

  # Contact lens (call analytics) - optional, adds cost
  contact_lens_enabled = false  # Enable later if needed

  # Auto resolve best practice warnings
  auto_resolve_best_voices_enabled = true

  tags = {
    Name        = "${var.prefix}-connect-instance-${var.environment}"
    Environment = var.environment
    Project     = "ProjectForce"
    Phase       = "3"
    ManagedBy   = "Terraform"
  }
}

# ============================================================================
# Storage Configuration (Call Recordings)
# ============================================================================

resource "aws_s3_bucket" "call_recordings" {
  bucket = "${var.prefix}-call-recordings-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "${var.prefix}-call-recordings-${var.environment}"
    Environment = var.environment
    Purpose     = "AWS Connect Call Recordings"
  }
}

resource "aws_s3_bucket_versioning" "call_recordings" {
  bucket = aws_s3_bucket.call_recordings.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "call_recordings" {
  bucket = aws_s3_bucket.call_recordings.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy for recordings (90 days retention)
resource "aws_s3_bucket_lifecycle_configuration" "call_recordings" {
  bucket = aws_s3_bucket.call_recordings.id

  rule {
    id     = "delete-old-recordings"
    status = "Enabled"

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "call_recordings" {
  bucket = aws_s3_bucket.call_recordings.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ============================================================================
# Connect Instance Storage Config
# ============================================================================

resource "aws_connect_instance_storage_config" "call_recordings" {
  instance_id   = aws_connect_instance.main.id
  resource_type = "CALL_RECORDINGS"

  storage_config {
    s3_config {
      bucket_name   = aws_s3_bucket.call_recordings.id
      bucket_prefix = "recordings"

      encryption_config {
        encryption_type = "KMS"
        key_id          = aws_kms_key.connect_recordings.arn
      }
    }
    storage_type = "S3"
  }
}

resource "aws_connect_instance_storage_config" "contact_trace_records" {
  instance_id   = aws_connect_instance.main.id
  resource_type = "CONTACT_TRACE_RECORDS"

  storage_config {
    s3_config {
      bucket_name   = aws_s3_bucket.call_recordings.id
      bucket_prefix = "contact-trace-records"

      encryption_config {
        encryption_type = "KMS"
        key_id          = aws_kms_key.connect_recordings.arn
      }
    }
    storage_type = "S3"
  }
}

# KMS key for encryption
resource "aws_kms_key" "connect_recordings" {
  description             = "KMS key for AWS Connect call recordings"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  tags = {
    Name        = "${var.prefix}-connect-kms-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_kms_alias" "connect_recordings" {
  name          = "alias/${var.prefix}-connect-recordings-${var.environment}"
  target_key_id = aws_kms_key.connect_recordings.key_id
}

# ============================================================================
# Hours of Operation
# ============================================================================

resource "aws_connect_hours_of_operation" "main" {
  instance_id = aws_connect_instance.main.id
  name        = "${var.prefix}-24x7-hours"
  description = "24/7 Hours for AI voice assistant"
  time_zone   = "America/New_York"

  config {
    day = "MONDAY"
    start_time {
      hours   = 0
      minutes = 0
    }
    end_time {
      hours   = 23
      minutes = 59
    }
  }

  config {
    day = "TUESDAY"
    start_time {
      hours   = 0
      minutes = 0
    }
    end_time {
      hours   = 23
      minutes = 59
    }
  }

  config {
    day = "WEDNESDAY"
    start_time {
      hours   = 0
      minutes = 0
    }
    end_time {
      hours   = 23
      minutes = 59
    }
  }

  config {
    day = "THURSDAY"
    start_time {
      hours   = 0
      minutes = 0
    }
    end_time {
      hours   = 23
      minutes = 59
    }
  }

  config {
    day = "FRIDAY"
    start_time {
      hours   = 0
      minutes = 0
    }
    end_time {
      hours   = 23
      minutes = 59
    }
  }

  config {
    day = "SATURDAY"
    start_time {
      hours   = 0
      minutes = 0
    }
    end_time {
      hours   = 23
      minutes = 59
    }
  }

  config {
    day = "SUNDAY"
    start_time {
      hours   = 0
      minutes = 0
    }
    end_time {
      hours   = 23
      minutes = 59
    }
  }

  tags = {
    Name = "${var.prefix}-24x7-hours-${var.environment}"
  }
}

# ============================================================================
# Queue for handling calls
# ============================================================================

resource "aws_connect_queue" "main" {
  instance_id           = aws_connect_instance.main.id
  name                  = "${var.prefix}-voice-queue"
  description           = "Main queue for voice calls"
  hours_of_operation_id = aws_connect_hours_of_operation.main.hours_of_operation_id

  tags = {
    Name = "${var.prefix}-voice-queue-${var.environment}"
  }
}

# ============================================================================
# Phone Number (Note: Must be claimed manually first, then imported)
# ============================================================================

# NOTE: Phone numbers must be claimed through AWS Console first
# Then import using: terraform import aws_connect_phone_number.main <instance_id>:<phone_number_id>
#
# After claiming the number in AWS Console:
# 1. Get the phone number ID
# 2. Run: terraform import aws_connect_phone_number.main <instance_id>:<phone_number_id>
# 3. Uncomment the resource below

# resource "aws_connect_phone_number" "main" {
#   country_code = "US"
#   type         = "TOLL_FREE"  # or "DID" for direct dial
#
#   target_arn = aws_connect_instance.main.arn
#
#   tags = {
#     Name        = "${var.prefix}-phone-number-${var.environment}"
#     Environment = var.environment
#   }
# }

# ============================================================================
# Outputs
# ============================================================================

output "connect_instance_id" {
  description = "AWS Connect Instance ID"
  value       = aws_connect_instance.main.id
}

output "connect_instance_arn" {
  description = "AWS Connect Instance ARN"
  value       = aws_connect_instance.main.arn
}

output "connect_instance_url" {
  description = "AWS Connect Instance URL"
  value       = "https://${aws_connect_instance.main.instance_alias}.my.connect.aws"
}

output "call_recordings_bucket" {
  description = "S3 bucket for call recordings"
  value       = aws_s3_bucket.call_recordings.id
}

output "connect_queue_id" {
  description = "AWS Connect Queue ID"
  value       = aws_connect_queue.main.queue_id
}

output "connect_queue_arn" {
  description = "AWS Connect Queue ARN"
  value       = aws_connect_queue.main.arn
}
