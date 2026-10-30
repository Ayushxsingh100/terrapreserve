output "rds_endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.main.endpoint
}

output "rds_arn" {
  description = "RDS ARN"
  value       = aws_db_instance.main.arn
}
