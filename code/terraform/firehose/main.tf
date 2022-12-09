
#################################
###    Kinesis Firehose       ###
#################################

resource "aws_kinesis_firehose_delivery_stream" "s3_stream" {
  name        = "${var.deployment_name}-kinesis-firehose"
  destination = "extended_s3"

  extended_s3_configuration {
    role_arn        = aws_iam_role.firehose_role.arn
    bucket_arn      = var.s3_destination_bucket_arn
    buffer_size     = 128
    buffer_interval = 900

    prefix              = "!{timestamp:yyyy}/!{timestamp:MM}/!{timestamp:dd}/"
    error_output_prefix = "!{timestamp:yyyy}/!{timestamp:MM}/!{timestamp:dd}/errors/!{firehose:error-output-type}"

    # buffer_size = 128
    # buffer_interval = 600

    data_format_conversion_configuration {
      input_format_configuration {
        deserializer {
          hive_json_ser_de {}
        }
      }

      output_format_configuration {
        serializer {
          parquet_ser_de {
            compression = "GZIP"
          }
        }
      }

      schema_configuration {
        database_name = aws_glue_catalog_database.glue_catalog_database.name
        table_name    = aws_glue_catalog_table.glue_catalog_table.name
        role_arn      = aws_iam_role.firehose_role.arn
      }
    }
  }
}

######################################################
###    IAM role + policies Kinesies Firehose       ###
######################################################

resource "aws_iam_role" "firehose_role" {
  name = "${var.deployment_name}-firehose-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "firehose.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

data "aws_iam_policy_document" "s3_policy" {
  statement {
    effect = "Allow"
    actions = [
      "s3:AbortMultipartUpload",
      "s3:GetBucketLocation",
      "s3:GetObject",
      "s3:ListBucket",
      "s3:ListBucketMultipartUploads",
      "s3:PutObject",
    ]

    resources = [
      "arn:aws:s3:::${var.s3_destination_bucket}",
      "arn:aws:s3:::${var.s3_destination_bucket}/*"
    ]
  }
}

data "aws_iam_policy_document" "kinesis_firehose_access_glue_assume_policy" {
  statement {
    effect    = "Allow"
    actions   = ["glue:GetTableVersions"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "kinesis_firehose_access_glue_policy" {
  name   = "${var.deployment_name}-kinesis-firehose-access-glue-policy"
  role   = aws_iam_role.firehose_role.name
  policy = data.aws_iam_policy_document.kinesis_firehose_access_glue_assume_policy.json
}

resource "aws_iam_role_policy" "s3_policy" {
  name   = "${var.deployment_name}-s3-policy"
  role   = aws_iam_role.firehose_role.name
  policy = data.aws_iam_policy_document.s3_policy.json
}

#######################################
###  IAM policy for Lambda Scrape IAM Role ###
#######################################

data "aws_iam_policy_document" "kinesis_put" {
  statement {
    effect = "Allow"
    actions = [
      "firehose:PutRecord",
      "firehose:PutRecordBatch",
    ]

    resources = [
      aws_kinesis_firehose_delivery_stream.s3_stream.arn
    ]
  }
}

resource "aws_iam_role_policy" "kinesis_put" {
  name   = "${var.deployment_name}-kinesis-put-policy"
  role   = var.iam_role_lambda_scrape_name
  policy = data.aws_iam_policy_document.kinesis_put.json
}

######################################
###    Glue Database + Table       ###
######################################

resource "aws_glue_catalog_database" "glue_catalog_database" {
  name = var.glue_catalog_database_name
}

resource "aws_glue_catalog_table" "glue_catalog_table" {
  name          = var.glue_catalog_table_name
  database_name = aws_glue_catalog_database.glue_catalog_database.name

  parameters = {
    "classification" = "parquet"
  }

  storage_descriptor {
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
    location      = "s3://${var.s3_destination_bucket}/"

    ser_de_info {
      name                  = "JsonSerDe"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"

      parameters = {
        "serialization.format" = 1
        "explicit.null"        = false
        "parquet.compression"  = "GZIP"
      }
    }
    columns {
      name = "domain"
      type = "string"
    }

    columns {
      name = "url"
      type = "string"
    }

    columns {
      name = "page_text"
      type = "string"
    }

    columns {
      name = "page_links"
      type = "string"
    }

    columns {
      name = "job_tag"
      type = "string"
    }

    columns {
      name = "timestamp"
      type = "string"
    }

  }
}
