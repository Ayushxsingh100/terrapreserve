# OUTPUTS FOR RDS MODULE

output "rds_endpoint" {
  description = "The connection endpointin address:port format."
  value       = aws_db_instance.this.endpoint
}

output "db_instance_id" {
  description = "The RDS instance ID"
  value       = aws_db_instance.this.id
}
