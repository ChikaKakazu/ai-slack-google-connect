data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "lambda_policy" {
  # DynamoDB access
  statement {
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
    ]
    resources = [
      aws_dynamodb_table.conversations.arn,
      aws_dynamodb_table.oauth_tokens.arn,
    ]
  }

  # Secrets Manager access
  statement {
    actions = [
      "secretsmanager:GetSecretValue",
    ]
    resources = [
      aws_secretsmanager_secret.slack_secrets.arn,
      aws_secretsmanager_secret.google_secrets.arn,
    ]
  }

  # Bedrock access
  statement {
    actions = [
      "bedrock:InvokeModel",
    ]
    resources = [
      "arn:aws:bedrock:*::foundation-model/anthropic.*",
      "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/apac.anthropic.*",
    ]
  }

  # AWS Marketplace access (required for Bedrock model auto-subscription)
  statement {
    actions = [
      "aws-marketplace:ViewSubscriptions",
      "aws-marketplace:Subscribe",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "lambda_policy" {
  name   = "${var.project_name}-lambda-policy-${var.environment}"
  role   = aws_iam_role.lambda_role.id
  policy = data.aws_iam_policy_document.lambda_policy.json
}
