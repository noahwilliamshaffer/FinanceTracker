# Terraform Variables for Finance Tracker Infrastructure
#
# This file defines all input variables used to configure the infrastructure.
# Variables provide flexibility for different environments and configurations.

# AWS Configuration Variables
variable "aws_region" {
  description = "AWS region for resource deployment"
  type        = string
  default     = "us-east-1"
  
  validation {
    condition = contains([
      "us-east-1", "us-east-2", "us-west-1", "us-west-2",
      "eu-west-1", "eu-west-2", "eu-central-1"
    ], var.aws_region)
    error_message = "AWS region must be a valid region for financial services."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

# S3 Configuration Variables
variable "s3_versioning_enabled" {
  description = "Enable S3 bucket versioning for audit compliance"
  type        = bool
  default     = true
}

variable "s3_encryption_algorithm" {
  description = "S3 server-side encryption algorithm"
  type        = string
  default     = "AES256"
  
  validation {
    condition     = contains(["AES256", "aws:kms"], var.s3_encryption_algorithm)
    error_message = "S3 encryption algorithm must be AES256 or aws:kms."
  }
}

variable "s3_lifecycle_ia_days" {
  description = "Days after which to transition objects to Infrequent Access"
  type        = number
  default     = 30
  
  validation {
    condition     = var.s3_lifecycle_ia_days >= 30
    error_message = "Transition to IA must be at least 30 days."
  }
}

variable "s3_lifecycle_glacier_days" {
  description = "Days after which to transition objects to Glacier"
  type        = number
  default     = 90
  
  validation {
    condition     = var.s3_lifecycle_glacier_days >= 90
    error_message = "Transition to Glacier must be at least 90 days."
  }
}

variable "s3_lifecycle_expiration_days" {
  description = "Days after which to expire/delete objects"
  type        = number
  default     = 2555  # 7 years for financial compliance
  
  validation {
    condition     = var.s3_lifecycle_expiration_days >= 365
    error_message = "Object expiration must be at least 1 year for financial compliance."
  }
}

# Lambda Configuration Variables
variable "lambda_runtime" {
  description = "Python runtime version for Lambda functions"
  type        = string
  default     = "python3.11"
  
  validation {
    condition     = contains(["python3.9", "python3.10", "python3.11"], var.lambda_runtime)
    error_message = "Lambda runtime must be a supported Python version."
  }
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 300
  
  validation {
    condition     = var.lambda_timeout >= 30 && var.lambda_timeout <= 900
    error_message = "Lambda timeout must be between 30 and 900 seconds."
  }
}

variable "lambda_memory_size" {
  description = "Lambda function memory allocation in MB"
  type        = number
  default     = 512
  
  validation {
    condition     = var.lambda_memory_size >= 128 && var.lambda_memory_size <= 3008
    error_message = "Lambda memory must be between 128 and 3008 MB."
  }
}

variable "lambda_log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 30
  
  validation {
    condition = contains([
      1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653
    ], var.lambda_log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch retention period."
  }
}

# EventBridge Configuration Variables
variable "eventbridge_archive_retention_days" {
  description = "EventBridge event archive retention period in days"
  type        = number
  default     = 7
  
  validation {
    condition     = var.eventbridge_archive_retention_days >= 1 && var.eventbridge_archive_retention_days <= 365
    error_message = "EventBridge archive retention must be between 1 and 365 days."
  }
}

# Monitoring and Alerting Variables
variable "cloudwatch_alarm_email" {
  description = "Email address for CloudWatch alarm notifications"
  type        = string
  default     = "noahwilliamshaffer@gmail.com"
  
  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.cloudwatch_alarm_email))
    error_message = "Must be a valid email address."
  }
}

variable "lambda_error_threshold" {
  description = "Number of Lambda errors before triggering alarm"
  type        = number
  default     = 5
  
  validation {
    condition     = var.lambda_error_threshold >= 1 && var.lambda_error_threshold <= 100
    error_message = "Error threshold must be between 1 and 100."
  }
}

variable "data_freshness_threshold_minutes" {
  description = "Maximum age of data in minutes before triggering freshness alarm"
  type        = number
  default     = 240  # 4 hours
  
  validation {
    condition     = var.data_freshness_threshold_minutes >= 30
    error_message = "Data freshness threshold must be at least 30 minutes."
  }
}

# Security Configuration Variables
variable "enable_vpc_endpoints" {
  description = "Enable VPC endpoints for AWS services"
  type        = bool
  default     = false
}

variable "enable_kms_encryption" {
  description = "Use KMS encryption instead of AES256 for S3"
  type        = bool
  default     = false
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access resources (if VPC is used)"
  type        = list(string)
  default     = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
}

# Data Processing Configuration Variables
variable "treasury_fetch_schedule" {
  description = "EventBridge schedule expression for treasury data fetching"
  type        = string
  default     = "rate(4 hours)"  # Fetch every 4 hours during market hours
  
  validation {
    condition = can(regex("^(rate\\([0-9]+ (minute|minutes|hour|hours|day|days)\\)|cron\\(.+\\))$", var.treasury_fetch_schedule))
    error_message = "Schedule must be a valid EventBridge rate or cron expression."
  }
}

variable "repo_fetch_schedule" {
  description = "EventBridge schedule expression for repo data fetching"
  type        = string
  default     = "rate(2 hours)"  # Fetch every 2 hours for more frequent repo updates
  
  validation {
    condition = can(regex("^(rate\\([0-9]+ (minute|minutes|hour|hours|day|days)\\)|cron\\(.+\\))$", var.repo_fetch_schedule))
    error_message = "Schedule must be a valid EventBridge rate or cron expression."
  }
}

variable "score_calculation_schedule" {
  description = "EventBridge schedule expression for score calculations"
  type        = string
  default     = "rate(1 hour)"  # Calculate scores hourly
  
  validation {
    condition = can(regex("^(rate\\([0-9]+ (minute|minutes|hour|hours|day|days)\\)|cron\\(.+\\))$", var.score_calculation_schedule))
    error_message = "Schedule must be a valid EventBridge rate or cron expression."
  }
}

# Cost Optimization Variables
variable "enable_s3_intelligent_tiering" {
  description = "Enable S3 Intelligent Tiering for cost optimization"
  type        = bool
  default     = true
}

variable "lambda_reserved_concurrency" {
  description = "Reserved concurrency limit for Lambda functions (null for unreserved)"
  type        = number
  default     = null
  
  validation {
    condition     = var.lambda_reserved_concurrency == null || (var.lambda_reserved_concurrency >= 1 && var.lambda_reserved_concurrency <= 1000)
    error_message = "Reserved concurrency must be null or between 1 and 1000."
  }
}

# Feature Flags
variable "enable_data_validation" {
  description = "Enable data validation Lambda function"
  type        = bool
  default     = true
}

variable "enable_audit_logging" {
  description = "Enable comprehensive audit logging"
  type        = bool
  default     = true
}

variable "enable_performance_monitoring" {
  description = "Enable detailed performance monitoring and dashboards"
  type        = bool
  default     = true
}

# External API Configuration
variable "external_api_rate_limits" {
  description = "Rate limits for external API calls (requests per minute)"
  type = object({
    treasury_api = number
    repo_api     = number
  })
  default = {
    treasury_api = 60   # 1 request per second
    repo_api     = 30   # 1 request per 2 seconds
  }
  
  validation {
    condition     = var.external_api_rate_limits.treasury_api >= 1 && var.external_api_rate_limits.repo_api >= 1
    error_message = "API rate limits must be at least 1 request per minute."
  }
}
