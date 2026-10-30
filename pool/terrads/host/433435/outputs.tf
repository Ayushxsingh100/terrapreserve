output "security_group_name" {
  description = "Name of the security group"
  value = aws_security_group.cw_sg_ssh.name
}
