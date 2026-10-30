output "rds_security_group_id" {
  description = "ID of the RDS security group"
  value       = aws_security_group.rds_sg.id
}

output "eks_to_rds_security_group_id" {
  description = "ID of the EKS to RDS security group"
  value       = aws_security_group.eks_to_rds_sg.id
}