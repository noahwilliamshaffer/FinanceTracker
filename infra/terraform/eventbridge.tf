# EventBridge Infrastructure for Finance Tracker
#
# This file creates the EventBridge custom event bus, rules, and targets
# for the event-driven data pipeline architecture.

# Custom EventBridge Event Bus for Finance Tracker events
resource "aws_cloudwatch_event_bus" "finance_tracker" {
  name = local.resource_names.event_bus
  
  tags = merge(local.common_tags, {
    Name    = local.resource_names.event_bus
    Purpose = "EventDrivenPipeline"
    Service = "EventBridge"
  })
}

# EventBridge Archive for event replay and audit
resource "aws_cloudwatch_event_archive" "finance_tracker" {
  name             = "${local.name_prefix}-event-archive"
  event_source_arn = aws_cloudwatch_event_bus.finance_tracker.arn
  
  description      = "Archive for Finance Tracker events for replay and audit purposes"
  retention_days   = var.eventbridge_archive_retention_days
  
  event_pattern = jsonencode({
    source = ["finance.treasury", "finance.repo", "finance.scoring"]
  })
}

# Treasury Data Update Rule
resource "aws_cloudwatch_event_rule" "treasury_data_updates" {
  name        = "${local.name_prefix}-treasury-data-updates"
  description = "Triggers when treasury market data is updated"
  
  event_bus_name = aws_cloudwatch_event_bus.finance_tracker.name
  
  event_pattern = jsonencode({
    source      = ["finance.treasury"]
    detail-type = ["Treasury Data Update", "Treasury Price Update"]
    detail = {
      status = ["success", "partial"]
    }
  })
  
  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-treasury-data-updates"
    Purpose     = "TreasuryDataProcessing"
    EventSource = "finance.treasury"
  })
}

# Repo Data Update Rule
resource "aws_cloudwatch_event_rule" "repo_data_updates" {
  name        = "${local.name_prefix}-repo-data-updates"
  description = "Triggers when repo market data is updated"
  
  event_bus_name = aws_cloudwatch_event_bus.finance_tracker.name
  
  event_pattern = jsonencode({
    source      = ["finance.repo"]
    detail-type = ["Repo Data Update", "Repo Spread Update"]
    detail = {
      status = ["success", "partial"]
    }
  })
  
  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-repo-data-updates"
    Purpose     = "RepoDataProcessing"
    EventSource = "finance.repo"
  })
}

# Scoring Calculation Rule - triggered by data updates
resource "aws_cloudwatch_event_rule" "scoring_calculations" {
  name        = "${local.name_prefix}-scoring-calculations"
  description = "Triggers scoring calculations after data updates"
  
  event_bus_name = aws_cloudwatch_event_bus.finance_tracker.name
  
  event_pattern = jsonencode({
    source      = ["finance.treasury", "finance.repo"]
    detail-type = ["Treasury Data Update", "Repo Data Update"]
    detail = {
      status = ["success"]
      # Only trigger scoring for successful data updates
    }
  })
  
  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-scoring-calculations"
    Purpose     = "ScoringCalculation"
    EventSource = "finance.data"
  })
}

# Data Quality Alert Rule - for failed updates or quality issues
resource "aws_cloudwatch_event_rule" "data_quality_alerts" {
  name        = "${local.name_prefix}-data-quality-alerts"
  description = "Triggers alerts for data quality issues"
  
  event_bus_name = aws_cloudwatch_event_bus.finance_tracker.name
  
  event_pattern = jsonencode({
    source      = ["finance.treasury", "finance.repo", "finance.validation"]
    detail-type = ["Data Quality Alert", "Validation Failure", "Data Update Failure"]
    detail = {
      severity = ["high", "critical"]
    }
  })
  
  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-data-quality-alerts"
    Purpose     = "DataQualityMonitoring"
    EventSource = "finance.validation"
  })
}

# Scheduled Rule for Treasury Data Fetching
resource "aws_cloudwatch_event_rule" "treasury_fetch_schedule" {
  name                = "${local.name_prefix}-treasury-fetch-schedule"
  description         = "Scheduled treasury data fetching"
  schedule_expression = var.treasury_fetch_schedule
  
  tags = merge(local.common_tags, {
    Name     = "${local.name_prefix}-treasury-fetch-schedule"
    Purpose  = "ScheduledDataFetch"
    DataType = "Treasury"
  })
}

# Scheduled Rule for Repo Data Fetching
resource "aws_cloudwatch_event_rule" "repo_fetch_schedule" {
  name                = "${local.name_prefix}-repo-fetch-schedule"
  description         = "Scheduled repo data fetching"
  schedule_expression = var.repo_fetch_schedule
  
  tags = merge(local.common_tags, {
    Name     = "${local.name_prefix}-repo-fetch-schedule"
    Purpose  = "ScheduledDataFetch"
    DataType = "Repo"
  })
}

# Scheduled Rule for Score Calculations
resource "aws_cloudwatch_event_rule" "score_calculation_schedule" {
  name                = "${local.name_prefix}-score-calculation-schedule"
  description         = "Scheduled score calculations"
  schedule_expression = var.score_calculation_schedule
  
  tags = merge(local.common_tags, {
    Name     = "${local.name_prefix}-score-calculation-schedule"
    Purpose  = "ScheduledScoring"
    DataType = "Scores"
  })
}

# EventBridge targets will be created in lambda.tf when Lambda functions are defined

# CloudWatch Event Rule for S3 data events
resource "aws_cloudwatch_event_rule" "s3_data_events" {
  name        = "${local.name_prefix}-s3-data-events"
  description = "Captures S3 data bucket events"
  
  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created", "Object Deleted"]
    detail = {
      bucket = {
        name = [aws_s3_bucket.data_bucket.bucket]
      }
    }
  })
  
  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-s3-data-events"
    Purpose     = "S3EventProcessing"
    EventSource = "aws.s3"
  })
}

# Dead Letter Queue for failed event processing
resource "aws_sqs_queue" "eventbridge_dlq" {
  name = "${local.name_prefix}-eventbridge-dlq"
  
  # Configure DLQ settings
  message_retention_seconds = 1209600  # 14 days
  visibility_timeout_seconds = 300     # 5 minutes
  
  # Enable server-side encryption
  sqs_managed_sse_enabled = true
  
  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-eventbridge-dlq"
    Purpose = "EventBridgeDeadLetterQueue"
    Service = "SQS"
  })
}

# DLQ Policy to allow EventBridge to send messages
resource "aws_sqs_queue_policy" "eventbridge_dlq_policy" {
  queue_url = aws_sqs_queue.eventbridge_dlq.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.eventbridge_dlq.arn
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = local.account_id
          }
        }
      }
    ]
  })
}

# CloudWatch Log Group for EventBridge rule execution logs
resource "aws_cloudwatch_log_group" "eventbridge_logs" {
  name              = "/aws/events/${local.name_prefix}"
  retention_in_days = var.lambda_log_retention_days
  
  tags = merge(local.common_tags, {
    Name    = "/aws/events/${local.name_prefix}"
    Purpose = "EventBridgeLogging"
    Service = "CloudWatch"
  })
}

# EventBridge Custom Metrics for monitoring
resource "aws_cloudwatch_metric_alarm" "eventbridge_failed_invocations" {
  count = var.enable_performance_monitoring ? 1 : 0
  
  alarm_name          = "${local.name_prefix}-eventbridge-failed-invocations"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "FailedInvocations"
  namespace           = "AWS/Events"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors EventBridge failed invocations"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]
  
  dimensions = {
    RuleName = aws_cloudwatch_event_rule.treasury_data_updates.name
  }
  
  tags = local.common_tags
}

# EventBridge Replay configuration for disaster recovery
resource "aws_cloudwatch_event_replay" "finance_tracker_replay" {
  count = var.environment == "prod" ? 1 : 0
  
  name             = "${local.name_prefix}-replay-config"
  description      = "Event replay configuration for disaster recovery"
  event_source_arn = aws_cloudwatch_event_bus.finance_tracker.arn
  
  destination {
    arn      = aws_cloudwatch_event_bus.finance_tracker.arn
    filter_arn = aws_cloudwatch_event_rule.treasury_data_updates.arn
  }
  
  event_start_time = "2024-01-01T00:00:00Z"
  event_end_time   = "2024-12-31T23:59:59Z"
}
