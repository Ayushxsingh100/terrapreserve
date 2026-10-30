locals {
  output_public_subnet = {
    for key in keys(local.public_subnets) : key => {
      subnet_id         = aws_subnet.this[key].id
      availability_Zone = aws_subnet.this[key].availability_zone
    }
  }
  output_private_subnet = {
    for key in keys(local.private_subnets) : key => {
      subnet_id         = aws_subnet.this[key].id
      availability_Zone = aws_subnet.this[key].availability_zone
    }
  }
}
output "vpc_id" {
  value       = aws_vpc.this.id
  description = "The VPC ID of the Created VPC"
}

output "public_subnets" {
  value       = local.output_public_subnet
  description = "The Subnet ID and AZ of the created Public Subnet"
}

output "private_aubnets" {
  value       = local.output_private_subnet
  description = "The Subnet ID and AZ of the created Private Subnet"
}

