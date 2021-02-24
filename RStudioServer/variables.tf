variable "deployment_name" {
  type = string
  description = "the deployment name will be used to name resources (e.g. EC2 server)"
}

variable "deployment_owner" {
  type = string
  description = "resources of this deployment will receive the owner tag"
}

variable "ip_whitelist" {
  type = list
  description = "the ip address that should be whitelisted"
  default = ["5.132.30.83/32"]
  
}

variable "instance_type" {
  type = string
  description = "instance type of the R studio server, this determines the number of available CPU cores and Memory"
  default = "t3.large"
}

# R studio
variable "rstudio_user" {
  type = string
  description = "the username that should be used for the R studio Login"
  default = "crunchbase"
}

variable "rstudio_user_pwd" {
  description = "the password of the R studio user"
  type = string
}

variable "rstudio_package_url" {
  type = string
  description = "the link to the R studio package that should be installed"
  default = "https://s3.amazonaws.com/rstudio-ide-build/server/centos7/x86_64/rstudio-server-rhel-1.4.1557-x86_64.rpm"
}

variable "rstudio_port" {
  type = string
  description = "the port on which R studio should be available"
  default = "8787"
}


