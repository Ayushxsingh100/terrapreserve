# ----
# Security Group
# ----

output "security_group_id" {
  description = "ID of the security group"
  value       = var.enabled ? aws_security_group.main[0].id : null
}

output "security_group_arn" {
  description = "ARN of the security group"
  value       = var.enabled ? aws_security_group.main[0].arn : null
}

output "security_group_name" {
  description = "Name of the security group"
  value       = var.enabled ? aws_security_group.main[0].name : null
}