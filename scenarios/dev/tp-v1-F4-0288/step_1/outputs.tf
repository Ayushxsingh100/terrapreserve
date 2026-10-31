output "Server-URL" {
  value = "http://${aws_instance.moscow-time-server.public_dns}"
}

output "SSH-command" {
  value = "ssh -i ~/.ssh/${var.keypair_name}.pem ubuntu@${aws_instance.moscow-time-server.public_dns}"
}
