output "rstudio_public_dns" {
  value       = "http://${aws_instance.rstudio-server.public_dns}:${var.rstudio_port}"
  description = "Master public DNS"
}