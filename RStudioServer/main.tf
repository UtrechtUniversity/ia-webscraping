#----------- EC2 instance --------

// data "aws_ami" "amazon-linux-2" {
//  most_recent = true
//  owners = ["amazon"]

//  filter {
//    name   = "name"
//    values = ["amzn2-ami-hvm*"]
//  }
// }

data "template_file" "install_rstudio" {
  template = file("./install_rstudio.sh")

  vars = {
    rstudio_user = var.rstudio_user
    rstudio_user_pwd = var.rstudio_user_pwd
    rstudio_url = var.rstudio_package_url
    rstudio_port = var.rstudio_port
  }
}

resource "aws_instance" "rstudio-server" {
  // ami           = data.aws_ami.amazon-linux-2.id
  ami = "ami-0518d8d22ae90fc37"
  instance_type = var.instance_type
  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name
  user_data = data.template_file.install_rstudio.rendered
  security_groups = [aws_security_group.crunchbase_rstudio_server.name]


  tags = {
    Name = var.deployment_name
    Owner = var.deployment_owner
  }
}

#----------- IAM instance profile --------

resource "aws_iam_policy" "ec2_policy" {
  name        = "ec2_rstudio_s3_policy_${var.deployment_name}"
  path        = "/"
  description = "Policy for ec2 rstudio server for s3 access"

  # Terraform's "jsonencode" function converts a
  # Terraform expression result to valid JSON syntax.
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:*",
        ]
        Effect   = "Allow"
        Resource = var.s3_buckets
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ec2_policy" {
  role       = aws_iam_role.role.name
  policy_arn = aws_iam_policy.ec2_policy.arn
  #policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "ec2_rstudio_profile_${var.deployment_name}"
  role = aws_iam_role.role.name
}

resource "aws_iam_role" "role" {
  name = "rstudio_role_${var.deployment_name}"
  path = "/"

  assume_role_policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": "sts:AssumeRole",
            "Principal": {
               "Service": "ec2.amazonaws.com"
            },
            "Effect": "Allow",
            "Sid": ""
        }
    ]
}
EOF
}

#--------- Security groups -----------

resource "aws_security_group" "crunchbase_rstudio_server" {
  name        = "rstudio-sg-${var.deployment_name}"
  description = "security group for crunchbase rstudio server for deployment ${var.deployment_name}"
  vpc_id      = "vpc-69e75903" #default vpc
}

resource "aws_security_group_rule" "ec2_rstudio_ingress" {
  description       = "Allow access to Rstudio for ip whitelist"
  from_port         = var.rstudio_port
  to_port           = var.rstudio_port
  cidr_blocks       = var.ip_whitelist
  protocol          = "tcp"
  security_group_id = aws_security_group.crunchbase_rstudio_server.id
  type              = "ingress"
}

resource "aws_security_group_rule" "ec2_rstudio_egress" {
  description       = "Allow all traffic out"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.crunchbase_rstudio_server.id
  type              = "egress"
}