output "aws_subnet_id" {
  value = aws_subnet.subnet.id
}

output "aws_security_group_id" {
  value = aws_security_group.ssh.id
}
