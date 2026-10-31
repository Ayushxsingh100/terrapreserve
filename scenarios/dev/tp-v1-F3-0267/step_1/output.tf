output "vpc_subnet_id" {
  value = aws_subnet.elk.id
}

output "security_group_id" {
  value = aws_security_group.elk_sg.id
}