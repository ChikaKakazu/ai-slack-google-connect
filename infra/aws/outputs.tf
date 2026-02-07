output "api_gateway_url" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.slack_bot.function_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.slack_bot.arn
}

output "conversations_table_name" {
  description = "DynamoDB conversations table name"
  value       = aws_dynamodb_table.conversations.name
}

output "oauth_tokens_table_name" {
  description = "DynamoDB OAuth tokens table name"
  value       = aws_dynamodb_table.oauth_tokens.name
}
