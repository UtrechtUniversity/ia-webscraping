resource "aws_cloudwatch_event_rule" "every_minute" {
  name        = "lambda-event-trigger"
  description = "trigger lambda every minute"
  schedule_expression = "rate(${var.trigger_rate} minutes)"
}

resource "aws_cloudwatch_event_target" "run_lambda_every_minute" {
    rule = aws_cloudwatch_event_rule.every_minute.name
    target_id = "test_lambda"
    arn = var.lambda_arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_check_foo" {
    statement_id = "AllowExecutionFromCloudWatch"
    action = "lambda:InvokeFunction"
    function_name = var.lambda_name
    principal = "events.amazonaws.com"
    source_arn = aws_cloudwatch_event_rule.every_minute.arn
}