provider "aws" {
  profile = "default"
  region  = "eu-central-1"
}

data "aws_iam_policy_document" "test_lambda_policy" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "test_lambda_role" {
  name               = "test_lambda_role"
  assume_role_policy = data.aws_iam_policy_document.test_lambda_policy.json
}

resource "aws_lambda_function" "test_lambda" {
  filename      = "package.zip"
  function_name = "test_lambda"
  role          = aws_iam_role.test_lambda_role.arn
  handler       = "main.lambda_handler"

  runtime = "python3.11"

  environment {
    variables = {
      foo = "bar"
    }
  }
}
