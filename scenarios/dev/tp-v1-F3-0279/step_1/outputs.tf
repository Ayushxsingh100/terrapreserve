#vpc
output "vpc_id" {
  value       = aws_vpc.main.id
  description = "The ID of the VPC"
}
locals {
  #if public == true then add to public_subnets
  public_subnet_output = { for key, subnet in local.public_subnets : key =>
    { subnet_id = aws_subnet.main[key].id
    subnet_az = aws_subnet.main[key].availability_zone }
  }
  private_subnet_output = { for key, subnet in local.private_subnets : key =>
    { subnet_id = aws_subnet.main[key].id
    subnet_az = aws_subnet.main[key].availability_zone }
  }
}
output "public_subnets" {
  value       = local.public_subnet_output
  description = "The IDs of the public subnets"
}

output "private_subnets" {
  value       = local.private_subnet_output
  description = "The IDs of the private subnets"
}
