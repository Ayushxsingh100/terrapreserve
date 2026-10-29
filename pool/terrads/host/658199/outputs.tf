output "database_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
}

output "database_name" {
  description = "Database name"
  value       = aws_db_instance.main.db_name
}

output "database_username" {
  description = "Database username"
  value       = aws_db_instance.main.username
}

output "database_port" {
  description = "Database port"
  value       = aws_db_instance.main.port
}

output "database_security_group_id" {
  description = "RDS security group ID"
  value       = aws_security_group.rds.id
}