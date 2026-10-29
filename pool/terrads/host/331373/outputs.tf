output "sg-id" {
  value       = aws_security_group.apache-sg.id
  description = "The ID of the apache security group"
}