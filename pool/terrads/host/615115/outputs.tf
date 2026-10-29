output "vpc_id" {
  description = "ID da VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs das subnets públicas em diferentes AZs"
  value       = [aws_subnet.public_az1.id, aws_subnet.public_az2.id]
}

output "security_group_ids" {
  description = "IDs dos Security Groups"
  value = [
    aws_security_group.ssh.id,
    aws_security_group.http.id,
    aws_security_group.db.id
  ]
}

output "alb_security_group_id" {
  description = "ID do Security Group para o Application Load Balancer"
  value       = aws_security_group.alb.id
}

