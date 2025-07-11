terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = ">= 4.41.0"
    }
  }
}

provider "aws" {
  profile = var.profile
  region  = var.source_region
}

variable "lambda_function_name" {
  default = "rds-backup"
  type = string
  description = "The name for the Lambda function. It will be used as prefix for roles, policies and log group."
}

variable "aws_account_id" {
  type = string
  description = "The AWS account ID where the function should be installed to."
}

variable "log_group_name" {
  default = "/aws/lambda/${var.lambda_function_name}"
  type = string
  description = "The name of the log group in CloudWatch Logs."
}

variable "source_region" {
  type = string
  description = "The source region where the source RDS lives and where the lambda will be configured."
}

variable "target_region" {
  type = string
  description = "The target region where the snapshots should be copied to."
}

variable "keep_snapshots" {
  type = number
  description = "Number of snapshots to be kept."
  default = 10
}

variable "target_kms" {
  type = string
  description = "The KMS key for the target region to use for encrytion of the snapshots."
}

variable "source_db" {
  type = list(string)
  description = "The name of the RDS instances to copy the snapshots."
}

variable "source_cluster" {
  type = list(string)
  description = "The name of the RDS cluster to copy the snapshots."
}

variable "profile" {
  type = string
  default = "default"
  description = "The AWS CLI profile to use."
}

# Lambda assume policy

data "aws_iam_policy_document" "lambda_assume_role_policy" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

# Scheduler assume policy

data "aws_iam_policy_document" "scheduler_assume_role_policy" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

# Lambda logging policy

data "aws_iam_policy_document" "lambda_logging_policy" {
  statement {
    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvent"
    ]

    resources = ["arn:aws:logs:${var.aws_account_id}:log-group:${var.log_group_name}:*"]
  }
}

# Lambda database snapshot policy

data "aws_iam_policy_document" "lambda_database_policy" {
  statement {
    effect = "Allow"

    actions = [
      "",
    ]
  }
}

# Scheduler Lambda invoke policy

data "aws_iam_policy_document" "scheduler_invoke_lambda_policy" {
  statement {
    effect = "Allow"

    actions = [
      "lambda:InvokeFunction"
    ]

    resources = lambda_function.arn
  }
}

# Lambda role with assume policy and inline policies for logging and database access

resource "aws_iam_role" "lambda_role" {
  name               = "${var.lambda_function_name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
  inline_policy {
    name = "logging"
    policy = data.aws_iam_policy_document.lambda_logging_policy.json
  }
  inline_policy {
    name = "database"
    policy = data.aws_iam_policy_document.lambda_database_policy.json
  }
}

# Scheduler role with assume policy and inline policies for invoking Lambda function

resource "aws_iam_role" "scheduler_role" {
  name               = "${var.lambda_function_name}-scheduler-role"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role_policy.json
  inline_policy {
    name = "invoke Lambda function"
    policy = data.aws_iam_policy_document.scheduler_invoke_lambda_policy.json
  }
}

# Cloudwatch log group

resource "aws_cloudwatch_log_group" "cw_log_group" {
  name = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = 14
}

# Scheduler rule

resource "aws_scheduler_schedule" "scheduler_daily" {
  name = "${var.lambda_function_name}-daily"
  description = "Daily backup of database snapshot from"
  group_name = "defaul"
  flexible_time_window {
    mode = "OFF"
  }
  schedule_expression = "rate(1 days)"
  target {
    arn = lambda_function.arn
    role_arn = aws_iam_role.scheduler_role.arn
    
  }
}

# Lambda function

resource "aws_lambda_function" "lambda_function" {
  filename      = "package.zip"
  function_name = var.lambda_function_name
  role          = aws_iam_role.lambda_role.arn
  handler       = "main.lambda_handler"

  runtime = "python3.13"
  architectures = ["arm64"]
  timeout = 10

  environment {
    variables = {
      AWS_ACCOUNT = var.aws_account_id
      SOURCE_REGION = var.source_region
      TARGET_REGION = var.target_region
      SOURCE_DB = "${join(",", var.source_db)}"
      SOURCE_CLUSTER = "${join(",", var.source_cluster)}"
      DEST_KMS = var.target_kms
      KEEP_SNAPSHOTS = var.keep_snapshots
    }
  }
}
