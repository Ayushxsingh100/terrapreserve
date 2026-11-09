output "aws_security_group_name" {
  description = "AWS security group name"
  value       = aws_security_group.sg.name
}
output "aws_security_group_id" {
  description = "AWS security group id"
  value       = aws_security_group.sg.id
}
output "aws_security_group_arn" {
  description = "AWS security group arn"
  value       = aws_security_group.sg.arn
}
