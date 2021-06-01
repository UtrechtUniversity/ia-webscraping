data "aws_s3_bucket_object" "lambda_code" {
  bucket = var.bucket_name
  key    = "cdx-records/${var.lambda_cdx}.zip"
}

resource "aws_lambda_function" "lambda" {
  function_name = var.lambda_name
  description = "aws lambda function"
  role          = aws_iam_role.iam_role_lambda.arn

  s3_bucket = data.aws_s3_bucket_object.lambda_code.bucket
  s3_key = data.aws_s3_bucket_object.lambda_code.key

  handler       = "main.handler"

  # Check hash code for code changes
  source_code_hash = chomp(file("../${var.lambda_name}.zip.sha256"))

  runtime = "python3.8"
  timeout = 120
  memory_size = "128"

  environment {
    variables = var.env_vars
  }
}

resource "aws_iam_role" "iam_for_lambda" {
  name = var.lambda_name

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

resource "aws_iam_policy" "sqs_send_policy" {
  name        = "sqs_send_policy"
  path        = "/"
  description = "SQS send policy example"

  # Terraform's "jsonencode" function converts a
  # Terraform expression result to valid JSON syntax.
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "sqs:SendMessage",
        ]
        Effect   = "Allow"
        Resource = var.sqs_fetch_arn
      },
    ]
  })
}



resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole"
}

resource "aws_iam_role_policy_attachment" "sqs_send" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = aws_iam_policy.sqs_send_policy.arn
}



