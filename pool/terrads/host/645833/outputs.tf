
output "eks_additional_security_group_id" {
  description = "ID of the additional EKS security group"
  value       = aws_security_group.eks_additional.id
}

output "alb_security_group_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb.id
}