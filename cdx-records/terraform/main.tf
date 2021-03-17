################################
### CDX-part of the pipeline ###
################################

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

resource "aws_iam_role_policy_attachment" "sqs_send" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = aws_iam_policy.sqs_send_policy.arn
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
        Resource = aws_sqs_queue.sqs_fetch_queue.arn
      },
    ]
  })
}

data "aws_s3_bucket_object" "lambda_code" {
  bucket = "crunchbase-dev-mvos-source"
  key    = "cdx-records/lambda-cdx-crunchbase-dev-mvos.zip"
}

resource "aws_sqs_queue" "sqs_cdx_queue" {
  name                      = "crunchbase-dev-mvos-lambda-cdx-queue"
  delay_seconds             = 10
  max_message_size          = 2048
  message_retention_seconds = 86400
  receive_wait_time_seconds = 10
}

resource "aws_sqs_queue" "sqs_fetch_queue" {
  name                      = "crunchbase-dev-mvos-lambda-fetch-queue"
  delay_seconds             = 10
  max_message_size          = 2048
  message_retention_seconds = 86400
  receive_wait_time_seconds = 10
  visibility_timeout_seconds = 45
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.failed_to_scrape.arn
    maxReceiveCount     = 1000
  })
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
  timeout = 120
  memory_size = "128"

  environment {
    variables = {
      sqs_cdx_id = aws_sqs_queue.sqs_cdx_queue.id,
      sqs_cdx_arn = aws_sqs_queue.sqs_cdx_queue.arn,
      sqs_fetch_id = aws_sqs_queue.sqs_fetch_queue.id,
      sqs_fetch_arn = aws_sqs_queue.sqs_fetch_queue.arn,
      target_bucket_id = aws_s3_bucket.result_bucket.id,
      sqs_fetch_limit = "1000",
      sqs_message_delay_increase = "10",
      sqs_cdx_max_messages = "10"
    }
  }

}

#################################
### Scraping part of pipeline ###
#################################

# Create bucket
resource "aws_s3_bucket" "result_bucket" {
  bucket = "crunchbase-scraping-results-csk" # bucket name
  acl    = "private"

  tags = {
    Name        = "scraping-result-bucket"
    Environment = "Dev"
  }
}

# This is my scraper lamda role
resource "aws_iam_role" "iam_for_scraper_lambda" {
  name="lambda-scraper-role-csk"

  # the dash '-' after << signifies that we are dealing
  # with an intended heredoc
  # Sid: ONLY CAMELCASE
  assume_role_policy = <<-POLICY
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": "sts:AssumeRole",
        "Principal": {
          "Service": "lambda.amazonaws.com"
        },
        "Sid": "lambdaRole",
        "Effect": "Allow"
      }
    ]
  }
  POLICY
}

# additional policies for scraper lambda
resource "aws_iam_policy" "lambda_logging" {
  name = "lambda-scraper-policies-csk"
  path="/"
  description = "IAM policy for logging, writing to bucket and listening to"
  policy=<<-POLICY
  {
    "Version": "2012-10-17",
    "Statement": [
        {
          "Sid": "Whatever",
          "Effect": "Allow",
          "Action": [
              "logs:CreateLogStream",
              "logs:CreateLogGroup",
              "logs:PutLogEvents"
          ],
          "Resource": "arn:aws:logs:*:*:*"
        }
    ]
  }
  POLICY
}

# writing to the bucket
resource "aws_iam_policy" "lambda_write_to_bucket" {
  name="lambda-scraper-write-to-bucket-csk"
  policy=<<-POLICY
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": [ "s3:PutObject" ],
        "Resource": [ "${aws_s3_bucket.result_bucket.arn}/*" ],
        "Effect": "Allow"
      }
    ]
  }
  POLICY
}

# policy to let lambda listen to sqs
resource "aws_iam_policy" "lambda_listens_to_sqs" {
  name="lambda-scraper-listens-to-sqs-csk"
  policy=<<-POLICY
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": [
          "sqs:DeleteMessage",
          "sqs:ReceiveMessage",
          "sqs:GetQueueAttributes"
        ],
        "Resource": [ "${aws_sqs_queue.sqs_fetch_queue.arn}" ],
        "Effect": "Allow"
      },
      {
        "Effect": "Allow",
        "Action": [
          "sqs:ListQueues"
        ],
        "Resource": "*"
      }
    ]
  }
  POLICY
}

# ATTACHING POLICIES TO LAMBDA ROLE
resource "aws_iam_role_policy_attachment" "lambda_policies_i" {
  role       = aws_iam_role.iam_for_scraper_lambda.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}
resource "aws_iam_role_policy_attachment" "lambda_policies_ii" {
  role       = aws_iam_role.iam_for_scraper_lambda.name
  policy_arn = aws_iam_policy.lambda_write_to_bucket.arn
}
resource "aws_iam_role_policy_attachment" "lambda_policies_iii" {
  role       = aws_iam_role.iam_for_scraper_lambda.name
  policy_arn = aws_iam_policy.lambda_listens_to_sqs.arn
}

data "aws_s3_bucket_object" "lambda_scraper" {
  bucket = "crunchbase-dev-mvos-source"
  key    = "cdx-records/lambda-scraper-dev-csk.zip"
}

# LAMBDA FUNCTION
resource "aws_lambda_function" "scraper" {
  function_name = "lambda-scraping-dev-csk"
  description = "scraping a given url into bucket"
  role= aws_iam_role.iam_for_scraper_lambda.arn

  s3_bucket = data.aws_s3_bucket_object.lambda_scraper.bucket
  s3_key = data.aws_s3_bucket_object.lambda_scraper.key

  handler="main.lambda_handler"
  # Check hash code for code changes
  source_code_hash = chomp(file("../lambda-scraper-dev-csk.zip.sha256"))
  
  runtime = "python3.8"
  timeout= 45
  memory_size = "128"
}

# the dead letter queue
resource "aws_sqs_queue" "failed_to_scrape" {
  name                      = "failed_to_scrape"
  delay_seconds             = 90
  max_message_size          = 2048
  message_retention_seconds = 86400
  receive_wait_time_seconds = 10
}

# THIS MAKES THE sqs_fetch_queue TRIGGER THE scraping LAMBDA
# ##########################################################
resource "aws_lambda_permission" "allows_fetch_sqs_to_trigger_scraper_lambda" {
  statement_id  = "AllowExecutionFromSQS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scraper.function_name
  principal     = "sqs.amazonaws.com"
  source_arn    = aws_sqs_queue.sqs_fetch_queue.arn
}

resource "aws_lambda_event_source_mapping" "trigger_scraper" {
  batch_size       = 5 # set the amount of messages send to the lambda
  event_source_arn = aws_sqs_queue.sqs_fetch_queue.arn
  enabled          = true
  function_name    = aws_lambda_function.scraper.arn
  depends_on = [aws_iam_policy.lambda_listens_to_sqs] # let's see if this works
}



#################################
###    Cloudwatch Trigger     ###
#################################

module "cloudwatch_trigger" {
    source = "./cloudwatch_trigger"
    lambda_name = aws_lambda_function.test_lambda.function_name
    lambda_arn = aws_lambda_function.test_lambda.arn
    trigger_rate = "3"
}