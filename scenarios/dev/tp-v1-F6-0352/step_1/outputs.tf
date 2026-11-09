output "rds_sg_id" {
  description = "RDS security group ID"
  value       = aws_security_group.rds.id
}

output "backend_sg_id" {
  description = "Backend security group ID"
  value       = aws_security_group.backend.id
}

output "frontend_sg_id" {
  description = "Frontend security group ID"
  value       = aws_security_group.frontend.id
}