resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole"
}

resource "aws_iam_role" "iam_for_lambda" {
  name = "lambda_example_rjbood"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

data "aws_s3_bucket_object" "lambda_code" {
  bucket = "rjbood-crunchbase-terraform-lambda-example"
  key    = "v1.0.5/example_lambda.zip"
}

resource "aws_sqs_queue" "sqs_example_queue" {
  name                      = "terraform-example-queue-rjbood"
  delay_seconds             = 10
  max_message_size          = 2048
  message_retention_seconds = 86400
  receive_wait_time_seconds = 10
}

resource "aws_lambda_function" "test_lambda" {
  function_name = "lambda_example_rjbood"
  description = "terraform lambda example"
  role          = aws_iam_role.iam_for_lambda.arn

  s3_bucket = data.aws_s3_bucket_object.lambda_code.bucket
  s3_key = data.aws_s3_bucket_object.lambda_code.key

  handler       = "main.handler"

  # Check hash code for code changes
  source_code_hash = chomp(file("../example_lambda.zip.sha256"))

  runtime = "python3.8"
  timeout = "30"
  memory_size = "128"

  environment {
    variables = {
      sqs_id = aws_sqs_queue.sqs_example_queue.id,
      sqs_arn = aws_sqs_queue.sqs_example_queue.arn
    }
  }

}

module "cloudwatch_trigger" {
    source = "./cloudwatch_trigger"
    lambda_name = aws_lambda_function.test_lambda.function_name
    lambda_arn = aws_lambda_function.test_lambda.arn
    trigger_rate = "3"
}