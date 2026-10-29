output "security_group_id" {
  description = "The ID of the security group."
  value       = length(aws_security_group.this) > 0 ? aws_security_group.this[0].id : null
}
