# Finance Tracker Infrastructure - Main Configuration
#
# This Terraform configuration creates the AWS infrastructure for the
# Finance Tracker event-driven data pipeline including S3 buckets,
# Lambda functions, EventBridge rules, and IAM roles.

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Backend configuration for state management
  backend "s3" {
    bucket         = "finance-tracker-terraform-state-783085491860"
    key            = "finance-tracker/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "finance-tracker-terraform-locks"
  }
}

# Configure the AWS Provider with account details
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "FinanceTracker"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "noahwilliamshaffer@gmail.com"
      AccountID   = "783085491860"
    }
  }
}

# Data source for current AWS account information
data "aws_caller_identity" "current" {}

# Data source for available AWS availability zones
data "aws_availability_zones" "available" {
  state = "available"
}

# Local values for resource naming and configuration
locals {
  # Account ID for resource naming
  account_id = data.aws_caller_identity.current.account_id
  
  # Common name prefix for all resources
  name_prefix = "finance-tracker"
  
  # Full resource names with environment suffix
  resource_names = {
    data_bucket     = "${local.name_prefix}-data-${local.account_id}"
    audit_bucket    = "${local.name_prefix}-audit-${local.account_id}"
    staging_bucket  = "${local.name_prefix}-staging-${local.account_id}"
    event_bus      = "${local.name_prefix}-events"
    lambda_role    = "${local.name_prefix}-lambda-role"
  }
  
  # Common tags applied to all resources
  common_tags = {
    Project     = "FinanceTracker"
    Environment = var.environment
    ManagedBy   = "Terraform"
    CreatedBy   = "noahwilliamshaffer@gmail.com"
    AccountID   = local.account_id
  }
}
