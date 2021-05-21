# This file declares terraform variables that are used in the main file
# Values are assigned in the terraform.tfvars file

 variable "sqs_name" {
     description = "human readable name of the sqs queue"
     type = string
     default = "my_queue"
 } 

 variable "delay_seconds" {
     description = "time that the delivery of all messages in the queue will be delayed"
     type = string
     default = "10"
 }  

variable "visibility_timeout_seconds" {
  description = "The visibility timeout for the queue"
  type        = number
  default     = 30
}

 variable "redrive_policy" {
  description = "JSON policy to set up the Dead Letter Queue"
  type        = string
  default     = ""
}