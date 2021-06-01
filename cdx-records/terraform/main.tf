################################
### LAMBDA FUNCTIONS ###
################################

module "lambda_cdx" {
    source = "./lambda"
    lambda_name = "${var.lambda_name}-cdx" 
    bucket_name = "crunchbase-dev-mvos-source"
    sqs_fetch_arn = module.sqs_fetch.sqs_arn

    env_vars = {
      sqs_cdx_id = module.sqs_cdx.sqs_id,
      sqs_cdx_arn = module.sqs_cdx.sqs_arn,
      sqs_message_delay_increase = var.sqs_message_delay_increase,
      sqs_cdx_max_messages = var.sqs_cdx_max_messages,
      cdx_lambda_n_iterations = var.cdx_lambda_n_iterations,
      cdx_logging_level = var.cdx_logging_level,
      cdx_run_id = var.cdx_run_id
        }
    }


#################################
###    SQS QUEUES    ###
#################################

module "sqs_cdx" {
  source   = "./sqs"
  sqs_name = "${var.lambda_cdx}-cdx-queue"
}

module "sqs_fetch" {
  source    = "./sqs"
  sqs_name  = "${var.lambda_cdx}-fetch-queue"
  visibility_timeout_seconds = 120
  redrive_policy = jsonencode({
    deadLetterTargetArn = module.scrape_letters.sqs_arn
    maxReceiveCount     = 1000
  })
}

module "scrape_letters" {
  source    = "./sqs"
  sqs_name  = "scrape_lambda_dead_letters"
  delay_seconds = 90
}

module "scrape_failures" {
  source    = "./sqs"
  sqs_name  = "scrape_failures"
  delay_seconds  = 90
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
        "Resource": [ "${module.sqs_fetch.sqs_arn}" ],
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

# policy to let lambda write to failure sqs
resource "aws_iam_policy" "lambda_sends_to_failure_sqs" {
  name        = "lambda_sends_to_failure_sqs"
  path        = "/"
  description = "SQS policy"

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
        Resource = module.scrape_failures.sqs_arn
      },
    ]
  })
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
resource "aws_iam_role_policy_attachment" "lambda_policies_iv" {
  role       = aws_iam_role.iam_for_scraper_lambda.name
  policy_arn = aws_iam_policy.lambda_sends_to_failure_sqs.arn
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
  timeout= 120
  memory_size = "128"

    
  environment {
    variables = {
      sqs_failures_id = module.scrape_failures.sqs_id,
      sqs_failures_arn = module.scrape_failures.sqs_arn,
      scraper_logging_level = var.scraper_logging_level
    }
  }
}


# THIS MAKES THE sqs_fetch_queue TRIGGER THE scraping LAMBDA
# ##########################################################
resource "aws_lambda_permission" "allows_fetch_sqs_to_trigger_scraper_lambda" {
  statement_id  = "AllowExecutionFromSQS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scraper.function_name
  principal     = "sqs.amazonaws.com"
  source_arn    = module.sqs_fetch.sqs_arn
}

resource "aws_lambda_event_source_mapping" "trigger_scraper" {
  batch_size       = 5 # set the amount of messages send to the lambda
  event_source_arn = module.sqs_fetch.sqs_arn
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