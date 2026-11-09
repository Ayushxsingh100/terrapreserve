output "rds_security_group_ids" {
  description = "Security group IDs for Aurora"
  value       = [aws_security_group.rds.id]
}
