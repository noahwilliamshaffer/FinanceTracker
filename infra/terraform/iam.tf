# IAM Infrastructure for Finance Tracker
#
# This file creates IAM roles, policies, and permissions for Lambda functions,
# EventBridge rules, and other AWS services with least-privilege access.

# Lambda Execution Role - Base role for all Lambda functions
resource "aws_iam_role" "lambda_execution_role" {
  name = local.resource_names.lambda_role
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name    = local.resource_names.lambda_role
    Purpose = "LambdaExecution"
    Service = "Lambda"
  })
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Attach X-Ray tracing policy for observability
resource "aws_iam_role_policy_attachment" "lambda_xray_write_access" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Custom policy for S3 access to data buckets
resource "aws_iam_policy" "lambda_s3_access" {
  name        = "${local.name_prefix}-lambda-s3-access"
  description = "S3 access policy for Finance Tracker Lambda functions"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:GetObjectVersion",
          "s3:PutObjectAcl"
        ]
        Resource = [
          "${aws_s3_bucket.data_bucket.arn}/*",
          "${aws_s3_bucket.staging_bucket.arn}/*",
          "${aws_s3_bucket.audit_bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:GetBucketVersioning"
        ]
        Resource = [
          aws_s3_bucket.data_bucket.arn,
          aws_s3_bucket.staging_bucket.arn,
          aws_s3_bucket.audit_bucket.arn
        ]
      }
    ]
  })
  
  tags = local.common_tags
}

# Attach S3 access policy to Lambda role
resource "aws_iam_role_policy_attachment" "lambda_s3_access" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_s3_access.arn
}

# Custom policy for EventBridge access
resource "aws_iam_policy" "lambda_eventbridge_access" {
  name        = "${local.name_prefix}-lambda-eventbridge-access"
  description = "EventBridge access policy for Finance Tracker Lambda functions"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "events:PutEvents",
          "events:DescribeRule",
          "events:ListTargetsByRule"
        ]
        Resource = [
          "arn:aws:events:${var.aws_region}:${local.account_id}:event-bus/${local.resource_names.event_bus}",
          "arn:aws:events:${var.aws_region}:${local.account_id}:rule/*"
        ]
      }
    ]
  })
  
  tags = local.common_tags
}

# Attach EventBridge access policy to Lambda role
resource "aws_iam_role_policy_attachment" "lambda_eventbridge_access" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_eventbridge_access.arn
}

# Custom policy for KMS access (if KMS encryption is enabled)
resource "aws_iam_policy" "lambda_kms_access" {
  count = var.enable_kms_encryption ? 1 : 0
  
  name        = "${local.name_prefix}-lambda-kms-access"
  description = "KMS access policy for Finance Tracker Lambda functions"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = [
          aws_kms_key.s3_encryption[0].arn
        ]
      }
    ]
  })
  
  tags = local.common_tags
}

# Attach KMS access policy to Lambda role (if enabled)
resource "aws_iam_role_policy_attachment" "lambda_kms_access" {
  count = var.enable_kms_encryption ? 1 : 0
  
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_kms_access[0].arn
}

# Custom policy for Secrets Manager access (for API keys)
resource "aws_iam_policy" "lambda_secrets_access" {
  name        = "${local.name_prefix}-lambda-secrets-access"
  description = "Secrets Manager access policy for Finance Tracker Lambda functions"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:${local.account_id}:secret:finance-tracker/*"
        ]
      }
    ]
  })
  
  tags = local.common_tags
}

# Attach Secrets Manager access policy to Lambda role
resource "aws_iam_role_policy_attachment" "lambda_secrets_access" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_secrets_access.arn
}

# Custom policy for CloudWatch metrics and alarms
resource "aws_iam_policy" "lambda_cloudwatch_access" {
  name        = "${local.name_prefix}-lambda-cloudwatch-access"
  description = "CloudWatch access policy for Finance Tracker Lambda functions"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "FinanceTracker"
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams",
          "logs:DescribeLogGroups"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${local.account_id}:log-group:/aws/lambda/${local.name_prefix}-*"
      }
    ]
  })
  
  tags = local.common_tags
}

# Attach CloudWatch access policy to Lambda role
resource "aws_iam_role_policy_attachment" "lambda_cloudwatch_access" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_cloudwatch_access.arn
}

# EventBridge Service Role for invoking Lambda functions
resource "aws_iam_role" "eventbridge_lambda_role" {
  name = "${local.name_prefix}-eventbridge-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-eventbridge-lambda-role"
    Purpose = "EventBridgeLambdaInvocation"
    Service = "EventBridge"
  })
}

# Policy for EventBridge to invoke Lambda functions
resource "aws_iam_policy" "eventbridge_lambda_invoke" {
  name        = "${local.name_prefix}-eventbridge-lambda-invoke"
  description = "Policy allowing EventBridge to invoke Lambda functions"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "arn:aws:lambda:${var.aws_region}:${local.account_id}:function:${local.name_prefix}-*"
      }
    ]
  })
  
  tags = local.common_tags
}

# Attach invoke policy to EventBridge role
resource "aws_iam_role_policy_attachment" "eventbridge_lambda_invoke" {
  role       = aws_iam_role.eventbridge_lambda_role.name
  policy_arn = aws_iam_policy.eventbridge_lambda_invoke.arn
}

# CloudWatch service role for cross-service monitoring
resource "aws_iam_role" "cloudwatch_service_role" {
  count = var.enable_performance_monitoring ? 1 : 0
  
  name = "${local.name_prefix}-cloudwatch-service-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.amazonaws.com"
        }
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-cloudwatch-service-role"
    Purpose = "CloudWatchMonitoring"
    Service = "CloudWatch"
  })
}

# Policy for enhanced CloudWatch monitoring
resource "aws_iam_policy" "cloudwatch_enhanced_monitoring" {
  count = var.enable_performance_monitoring ? 1 : 0
  
  name        = "${local.name_prefix}-cloudwatch-enhanced-monitoring"
  description = "Enhanced monitoring policy for Finance Tracker services"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetBucketMetricsConfiguration",
          "s3:GetBucketNotification",
          "s3:ListAllMyBuckets",
          "s3:ListBucket"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:GetFunction",
          "lambda:ListFunctions",
          "lambda:GetFunctionConfiguration"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "events:DescribeRule",
          "events:ListRules",
          "events:ListTargetsByRule"
        ]
        Resource = "*"
      }
    ]
  })
  
  tags = local.common_tags
}

# Attach enhanced monitoring policy
resource "aws_iam_role_policy_attachment" "cloudwatch_enhanced_monitoring" {
  count = var.enable_performance_monitoring ? 1 : 0
  
  role       = aws_iam_role.cloudwatch_service_role[0].name
  policy_arn = aws_iam_policy.cloudwatch_enhanced_monitoring[0].arn
}

# Data validation role with restricted permissions
resource "aws_iam_role" "data_validation_role" {
  count = var.enable_data_validation ? 1 : 0
  
  name = "${local.name_prefix}-data-validation-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-data-validation-role"
    Purpose = "DataValidation"
    Service = "Lambda"
  })
}

# Restricted policy for data validation (read-only access)
resource "aws_iam_policy" "data_validation_policy" {
  count = var.enable_data_validation ? 1 : 0
  
  name        = "${local.name_prefix}-data-validation-policy"
  description = "Restricted policy for data validation functions"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${aws_s3_bucket.data_bucket.arn}/*",
          aws_s3_bucket.data_bucket.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = [
          "${aws_s3_bucket.audit_bucket.arn}/validation-reports/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "events:PutEvents"
        ]
        Resource = "arn:aws:events:${var.aws_region}:${local.account_id}:event-bus/${local.resource_names.event_bus}"
      }
    ]
  })
  
  tags = local.common_tags
}

# Attach validation policy to validation role
resource "aws_iam_role_policy_attachment" "data_validation_basic" {
  count = var.enable_data_validation ? 1 : 0
  
  role       = aws_iam_role.data_validation_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "data_validation_policy" {
  count = var.enable_data_validation ? 1 : 0
  
  role       = aws_iam_role.data_validation_role[0].name
  policy_arn = aws_iam_policy.data_validation_policy[0].arn
}
