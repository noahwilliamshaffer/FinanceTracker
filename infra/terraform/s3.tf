# S3 Infrastructure for Finance Tracker Data Storage
#
# This file creates the S3 buckets and related resources for storing
# treasury data, repo data, audit logs, and staging files with proper
# versioning, encryption, and lifecycle management.

# KMS Key for S3 encryption (if KMS encryption is enabled)
resource "aws_kms_key" "s3_encryption" {
  count = var.enable_kms_encryption ? 1 : 0
  
  description             = "KMS key for Finance Tracker S3 bucket encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${local.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow Lambda service to use the key"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-s3-kms-key"
    Purpose     = "S3 Encryption"
    Compliance  = "FinancialData"
  })
}

# KMS Key Alias for easier management
resource "aws_kms_alias" "s3_encryption" {
  count = var.enable_kms_encryption ? 1 : 0
  
  name          = "alias/${local.name_prefix}-s3"
  target_key_id = aws_kms_key.s3_encryption[0].key_id
}

# Main Data Bucket - stores treasury and repo market data
resource "aws_s3_bucket" "data_bucket" {
  bucket = local.resource_names.data_bucket
  
  tags = merge(local.common_tags, {
    Name        = local.resource_names.data_bucket
    Purpose     = "MarketDataStorage"
    DataType    = "TreasuryAndRepo"
    Compliance  = "SOX,FinancialData"
  })
}

# Data bucket versioning configuration
resource "aws_s3_bucket_versioning" "data_bucket" {
  bucket = aws_s3_bucket.data_bucket.id
  
  versioning_configuration {
    status = var.s3_versioning_enabled ? "Enabled" : "Suspended"
  }
}

# Data bucket encryption configuration
resource "aws_s3_bucket_server_side_encryption_configuration" "data_bucket" {
  bucket = aws_s3_bucket.data_bucket.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.enable_kms_encryption ? "aws:kms" : var.s3_encryption_algorithm
      kms_master_key_id = var.enable_kms_encryption ? aws_kms_key.s3_encryption[0].arn : null
    }
    bucket_key_enabled = var.enable_kms_encryption
  }
}

# Data bucket public access block (security best practice)
resource "aws_s3_bucket_public_access_block" "data_bucket" {
  bucket = aws_s3_bucket.data_bucket.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Data bucket lifecycle configuration for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "data_bucket" {
  bucket = aws_s3_bucket.data_bucket.id
  depends_on = [aws_s3_bucket_versioning.data_bucket]
  
  rule {
    id     = "data_lifecycle"
    status = "Enabled"
    
    # Apply to all objects
    filter {}
    
    # Transition current version to IA after configured days
    transition {
      days          = var.s3_lifecycle_ia_days
      storage_class = "STANDARD_IA"
    }
    
    # Transition current version to Glacier after configured days
    transition {
      days          = var.s3_lifecycle_glacier_days
      storage_class = "GLACIER"
    }
    
    # Delete current version after configured days (compliance retention)
    expiration {
      days = var.s3_lifecycle_expiration_days
    }
    
    # Manage non-current versions
    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }
    
    noncurrent_version_transition {
      noncurrent_days = 60
      storage_class   = "GLACIER"
    }
    
    noncurrent_version_expiration {
      noncurrent_days = 365  # Keep old versions for 1 year
    }
    
    # Clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
  
  # Intelligent Tiering rule (if enabled)
  dynamic "rule" {
    for_each = var.enable_s3_intelligent_tiering ? [1] : []
    
    content {
      id     = "intelligent_tiering"
      status = "Enabled"
      
      filter {
        prefix = "intelligent-tiering/"
      }
      
      transition {
        days          = 0  # Immediate
        storage_class = "INTELLIGENT_TIERING"
      }
    }
  }
}

# Audit Bucket - stores audit logs and compliance data
resource "aws_s3_bucket" "audit_bucket" {
  bucket = local.resource_names.audit_bucket
  
  tags = merge(local.common_tags, {
    Name        = local.resource_names.audit_bucket
    Purpose     = "AuditLogging"
    DataType    = "AuditTrails"
    Compliance  = "SOX,Audit,Immutable"
  })
}

# Audit bucket versioning (always enabled for compliance)
resource "aws_s3_bucket_versioning" "audit_bucket" {
  bucket = aws_s3_bucket.audit_bucket.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Audit bucket encryption (always enabled)
resource "aws_s3_bucket_server_side_encryption_configuration" "audit_bucket" {
  bucket = aws_s3_bucket.audit_bucket.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.enable_kms_encryption ? "aws:kms" : "AES256"
      kms_master_key_id = var.enable_kms_encryption ? aws_kms_key.s3_encryption[0].arn : null
    }
    bucket_key_enabled = var.enable_kms_encryption
  }
}

# Audit bucket public access block
resource "aws_s3_bucket_public_access_block" "audit_bucket" {
  bucket = aws_s3_bucket.audit_bucket.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Audit bucket object lock for immutability (compliance requirement)
resource "aws_s3_bucket_object_lock_configuration" "audit_bucket" {
  bucket = aws_s3_bucket.audit_bucket.id
  
  rule {
    default_retention {
      mode = "COMPLIANCE"  # Cannot be overridden
      days = 2555         # 7 years
    }
  }
  
  object_lock_enabled = "Enabled"
}

# Audit bucket lifecycle (longer retention for compliance)
resource "aws_s3_bucket_lifecycle_configuration" "audit_bucket" {
  bucket = aws_s3_bucket.audit_bucket.id
  depends_on = [aws_s3_bucket_versioning.audit_bucket]
  
  rule {
    id     = "audit_lifecycle"
    status = "Enabled"
    
    filter {}
    
    # Keep in Standard for first year, then move to IA
    transition {
      days          = 365
      storage_class = "STANDARD_IA"
    }
    
    # Move to Glacier Deep Archive for long-term compliance storage
    transition {
      days          = 730  # 2 years
      storage_class = "DEEP_ARCHIVE"
    }
    
    # Never expire audit logs (compliance requirement)
    # expiration block is intentionally omitted
    
    # Manage non-current versions
    noncurrent_version_transition {
      noncurrent_days = 365
      storage_class   = "GLACIER"
    }
    
    noncurrent_version_expiration {
      noncurrent_days = 2555  # 7 years
    }
  }
}

# Staging Bucket - temporary storage for data processing
resource "aws_s3_bucket" "staging_bucket" {
  bucket = local.resource_names.staging_bucket
  
  tags = merge(local.common_tags, {
    Name        = local.resource_names.staging_bucket
    Purpose     = "DataStaging"
    DataType    = "Temporary"
    Lifecycle   = "ShortTerm"
  })
}

# Staging bucket versioning (optional for staging)
resource "aws_s3_bucket_versioning" "staging_bucket" {
  bucket = aws_s3_bucket.staging_bucket.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Staging bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "staging_bucket" {
  bucket = aws_s3_bucket.staging_bucket.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.enable_kms_encryption ? "aws:kms" : "AES256"
      kms_master_key_id = var.enable_kms_encryption ? aws_kms_key.s3_encryption[0].arn : null
    }
    bucket_key_enabled = var.enable_kms_encryption
  }
}

# Staging bucket public access block
resource "aws_s3_bucket_public_access_block" "staging_bucket" {
  bucket = aws_s3_bucket.staging_bucket.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Staging bucket lifecycle (aggressive cleanup for cost optimization)
resource "aws_s3_bucket_lifecycle_configuration" "staging_bucket" {
  bucket = aws_s3_bucket.staging_bucket.id
  depends_on = [aws_s3_bucket_versioning.staging_bucket]
  
  rule {
    id     = "staging_cleanup"
    status = "Enabled"
    
    filter {}
    
    # Delete staging files after 7 days
    expiration {
      days = 7
    }
    
    # Delete non-current versions after 1 day
    noncurrent_version_expiration {
      noncurrent_days = 1
    }
    
    # Clean up incomplete multipart uploads after 1 day
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# S3 Bucket Notifications for EventBridge integration
resource "aws_s3_bucket_notification" "data_bucket_notification" {
  bucket      = aws_s3_bucket.data_bucket.id
  eventbridge = true
  
  depends_on = [aws_s3_bucket.data_bucket]
}

# CloudWatch metrics for S3 bucket monitoring
resource "aws_cloudwatch_metric_alarm" "s3_data_bucket_size" {
  count = var.enable_performance_monitoring ? 1 : 0
  
  alarm_name          = "${local.name_prefix}-s3-data-bucket-size"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "BucketSizeBytes"
  namespace           = "AWS/S3"
  period              = "86400"  # 24 hours
  statistic           = "Average"
  threshold           = "107374182400"  # 100GB
  alarm_description   = "This metric monitors S3 data bucket size"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]
  
  dimensions = {
    BucketName  = aws_s3_bucket.data_bucket.bucket
    StorageType = "StandardStorage"
  }
  
  tags = local.common_tags
}
