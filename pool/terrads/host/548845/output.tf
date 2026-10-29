# Define output for the name of the provisioned security group

output "security_group_name" {
  value = aws_security_group.allow_ssh_http_https.name  # Output the name of the provisioned security group
}
