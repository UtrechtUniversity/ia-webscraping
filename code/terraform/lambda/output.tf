output "lambda_arn" {
  value       = aws_lambda_function.lambda.arn
  description = "The ARN of the lambda function"
}

output "lambda_name" {
  value       = aws_lambda_function.lambda.function_name
  description = "The name of the lambda function"
}

