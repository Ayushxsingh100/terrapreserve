output "id" {
  description = "ID of the security group."
  value       = try(aws_security_group.this[0].id, "")
}

output "arn" {
  description = "ARN of the security group."
  value       = try(aws_security_group.this[0].arn, "")
}

output "owner_id" {
  description = "Owner ID."
  value       = try(aws_security_group.this[0].owner_id, "")
}
