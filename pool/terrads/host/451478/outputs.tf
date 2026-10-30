output "security_group_info" {
  value = {
    id = aws_security_group.security_group_https_ssh.id
    arn = aws_security_group.security_group_https_ssh.arn
  }
}

output "security_group_id" {
  value = aws_security_group.security_group_https_ssh.id
}


output "security_group_arn" {
  value = aws_security_group.security_group_https_ssh.arn
}