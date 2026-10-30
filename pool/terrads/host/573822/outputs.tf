output "security_group_id" {
  description = "Id do grupo de segurança utilizado na instância ec2"
  value = aws_security_group.permitir_ssh_http.id
}