output "rds_instance_id" {
  value = aws_db_instance.postgres.id
}

output "rds_instance_endpoint" {
  value = aws_db_instance.postgres.endpoint
}

output "rds_instance_username" {
  value = aws_db_instance.postgres.username
}

output "rds_instance_password" {
  value = aws_db_instance.postgres.password
  sensitive = true
}