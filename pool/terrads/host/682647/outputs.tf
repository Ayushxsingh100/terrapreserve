# AWS Platform Module - Outputs

output "app_security_group_id" {
  value       = aws_security_group.app.id
  description = "Application security group ID"
}

# Uncomment when using EKS
# output "eks_cluster_endpoint" {
#   value       = module.eks.cluster_endpoint
#   description = "EKS cluster endpoint"
# }

# output "eks_cluster_name" {
#   value       = module.eks.cluster_name
#   description = "EKS cluster name"
# }

# Uncomment when using RDS
# output "rds_endpoint" {
#   value       = aws_db_instance.main.endpoint
#   description = "RDS endpoint"
# }
