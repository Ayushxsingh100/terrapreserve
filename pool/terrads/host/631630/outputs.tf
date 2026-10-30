# Salida para el ID del grupo de seguridad de EC2.
# Descripción: El ID del grupo de seguridad de EC2.
output "ec2_security_group_id" {
  description = "The ID of the EC2 security group"
  value       = aws_security_group.ec2.id
}

# Salida para el ID del grupo de seguridad de RDS.
# Descripción: El ID del grupo de seguridad de RDS.
output "rds_security_group_id" {
  description = "The ID of the RDS security group"
  value       = aws_security_group.rds.id
}

# Salida para el ID del grupo de seguridad del ALB.
# Descripción: El ID del grupo de seguridad del ALB.
output "alb_security_group_id" {
  description = "The ID of the ALB security group"
  value       = aws_security_group.alb.id
  
}