resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole"
}

resource "aws_iam_role" "iam_for_lambda" {
  name = "lambda-cdx-crunchbase-dev-mvos"

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
  bucket = "crunchbase-dev-mvos-source"
  key    = "cdx-records/lambda-cdx-crunchbase-dev-mvos.zip"
}

resource "aws_sqs_queue" "sqs_example_queue" {
  name                      = "crunchbase-dev-mvos-lambda-cdx-queue"
  delay_seconds             = 10
  max_message_size          = 2048
  message_retention_seconds = 86400
  receive_wait_time_seconds = 10
}

resource "aws_lambda_function" "test_lambda" {
  function_name = "lambda-cdx-crunchbase-dev-mvos"
  description = "terraform lambda cdx"
  role          = aws_iam_role.iam_for_lambda.arn

  s3_bucket = data.aws_s3_bucket_object.lambda_code.bucket
  s3_key = data.aws_s3_bucket_object.lambda_code.key

  handler       = "main.handler"

  # Check hash code for code changes
  source_code_hash = chomp(file("../lambda-cdx-crunchbase-dev-mvos.zip.sha256"))

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