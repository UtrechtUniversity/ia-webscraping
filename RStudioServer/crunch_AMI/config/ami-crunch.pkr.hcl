// variable "source_ami" {
//   type    = string
//   description = "Amazon linux 2 AMI; most recent"
//   // default = "ami-0bdf93799014acdc4"

//   # Optional: define a filter to automatically pick the latest version of an ami as source ami.
//   source_ami_filter {
//     filters = {
//       name                = "amzn2-ami-hvm*"
//       root-device-type    = "ebs"
//       virtualization-type = "hvm"
//     }
//     most_recent = true
//     owners      = ["amazon"]
//   }
// }

locals { timestamp = regex_replace(timestamp(), "[- TZ:]", "") }

# source blocks configure your builder plugins; your source is then used inside
# build blocks to create resources. A build block runs provisioners and
# post-processors on an instance created by the source.
source "amazon-ebs" "crunch-ami" {
  # the profile to use in the shared credentials file for AWS.
  // profile       = "default"

  source_ami_filter {
    filters = {
      name                = "amzn2-ami-hvm*"
      root-device-type    = "ebs"
      virtualization-type = "hvm"
    }
    most_recent = true
    owners      = ["amazon"]
  }
  
  ami_name      = "ami-crunch-${local.timestamp}"
  ami_description = "AMI for the Crunch benchmark project"

  # uncomment following line to create a public ami, default a private ami is created
  // ami_groups = ["all"]
  
  instance_type = "t2.micro"
  // source_ami    = var.source_ami

  ssh_username = "ec2-user"
}

# a build block invokes sources and runs provisioning steps on them.
build {
  sources = ["source.amazon-ebs.crunch-ami"]

  provisioner "shell" {
    execute_command = "echo 'packer' | sudo -S env {{ .Vars }} {{ .Path }}"
    environment_vars = [
        "RSTUDIO_URL=https://s3.amazonaws.com/rstudio-ide-build/server/centos7/x86_64/rstudio-server-rhel-1.4.1557-x86_64.rpm"
    ]
    script = "./scripts/configure-ami.sh"
  }
}