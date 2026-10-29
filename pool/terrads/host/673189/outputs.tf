# RDS Outputs

output "db_endpoint" {
  description = "The connection endpoint for the RDS instance"
  value       = aws_db_instance.this.endpoint
}

output "db_port" {
  description = "The port the RDS instance is listening on"
  value       = aws_db_instance.this.port
}

output "db_username" {
  description = "The master username for the RDS instance"
  value       = aws_db_instance.this.username
}

output "db_name" {
  description = "The initial database name"
  value       = aws_db_instance.this.db_name
}

output "db_arn" {
  description = "ARN of the RDS instance"
  value       = aws_db_instance.this.arn
}

output "db_id" {
  description = "ID of the RDS instance"
  value       = aws_db_instance.this.id
}

output "db_security_group_id" {
  description = "The security group ID for the RDS instance"
  value       = aws_security_group.db.id
}

output "db_host" {
  description = "The hostname of the RDS instance (without port)"
  value       = split(":", aws_db_instance.this.endpoint)[0]
}
