output "rds_endpoint" {
  description = "Endpoint of the RDS PostgreSQL instance"
  value       = aws_db_instance.dagster_postgres.endpoint
}

output "rds_instance_id" {
  description = "Identifier of the RDS PostgreSQL instance"
  value       = aws_db_instance.dagster_postgres.identifier
}