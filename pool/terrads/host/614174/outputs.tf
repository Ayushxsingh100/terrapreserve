# modules/security_groups/outputs.tf

output "vpn_endpoint_sg_id" {
  description = "ID of the Security Group for the Client VPN Endpoint"
  value       = aws_security_group.vpn_endpoint_sg.id
}

output "alb_sg_id" {
  description = "ID of the Security Group for the Application Load Balancer"
  value       = aws_security_group.alb_sg.id
}

output "ec2_sg_id" {
  description = "ID of the Security Group for the EC2 instances"
  value       = aws_security_group.ec2_sg.id
}

output "rds_sg_id" {
  description = "ID of the Security Group for the RDS instance"
  value       = aws_security_group.rds_sg.id
}
