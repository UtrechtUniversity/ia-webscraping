data "aws_s3_bucket_object" "lambda_code" {
  bucket = var.bucket_name
  key    = "cdx-records/${var.lambda_function}.zip"
}

data "aws_iam_policy_document" "basic" {
  statement {
    actions = ["sts:AssumeRole"]
    effect  = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}


resource "aws_iam_role" "iam_role_lambda" {
  name               = var.lambda_function
  assume_role_policy = data.aws_iam_policy_document.basic.json
}

# Make sure lambda is allowed basic execution
resource "aws_iam_role_policy_attachment" "basic" {
  role       = aws_iam_role.iam_role_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole"
}

resource "aws_iam_policy" "additional" {
  name   = var.lambda_function
  policy = var.policy.json
}

resource "aws_iam_role_policy_attachment" "additional" {
  role       = aws_iam_role.iam_role_lambda.name
  policy_arn = aws_iam_policy.additional.arn
}

resource "aws_lambda_function" "lambda" {
  function_name = var.lambda_function
  description   = "aws lambda function"
  role          = aws_iam_role.iam_role_lambda.arn

  s3_bucket = data.aws_s3_bucket_object.lambda_code.bucket
  s3_key    = data.aws_s3_bucket_object.lambda_code.key

  handler = "main.handler"

  # Check hash code for code changes
  source_code_hash = chomp(file("../${var.lambda_function}.zip.sha256"))

  runtime     = "python3.8"
  timeout     = 120
  memory_size = "128"

  environment {
    variables = var.env_vars
  }
}


