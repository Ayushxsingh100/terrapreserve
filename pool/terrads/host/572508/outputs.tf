output "vpc_terraform" {
  description = "The ID of the VPC created by the Terraform configuration."
  value       = aws_vpc.vpc_terraform.id
}

output "aws_internet_gateway" {
  description = "The ID of the Internet Gateway associated with the VPC created by the Terraform configuration."
  value       = aws_internet_gateway.igw_terraform.id
}

output "sg_firewall" {
  description = "The ID of the Security Group created by the Terraform configuration."
  value       = aws_security_group.terraform_sg.id
}
