output "webapp_security_group_id" {
  description = "ID of the webapp security group"
  value       = aws_security_group.webapp.id
}

output "database_security_group_id" {
  description = "ID of the database security group"
  value       = aws_security_group.database.id
}

output "bastion_security_group_id" {
  description = "ID of the bastion security group"
  value       = aws_security_group.bastion.id
}