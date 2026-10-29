output "ec2_instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.bastion.id
}

output "ec2_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.bastion.public_ip
}

output "ec2_private_ip" {
  description = "Private IP address of the EC2 instance"
  value       = aws_instance.bastion.private_ip
}

output "ec2_public_dns" {
  description = "Public DNS name of the EC2 instance"
  value       = aws_instance.bastion.public_dns
}

output "rds_endpoint" {
  description = "RDS instance endpoint (hostname only, without port)"
  value       = split(":", aws_db_instance.main.endpoint)[0]
}

output "rds_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "rds_identifier" {
  description = "RDS instance identifier"
  value       = aws_db_instance.main.identifier
}

output "security_group_api_id" {
  description = "Security Group ID for API"
  value       = aws_security_group.api.id
}

output "security_group_rds_id" {
  description = "Security Group ID for RDS"
  value       = aws_security_group.rds.id
}
