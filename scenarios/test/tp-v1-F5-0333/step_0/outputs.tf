
/*
1. vpc id
2. public subnets - ID = subnet_key => {subnet_id}
3. private subnets - ID = subnet_key => {subnet_id}

*/

locals {
  output_public_subnets = {
    for key in keys(local.public_subnets) : key => {
      subnet_id         = aws_subnet.subnet[key].id
      availability_zone = aws_subnet.subnet[key].availability_zone
      cidr_block        = aws_subnet.subnet[key].cidr_block
    }
  }
  output_private_subnets = {
    for key in keys(local.private_subnets) : key => {
      subnet_id         = aws_subnet.subnet[key].id
      availability_zone = aws_subnet.subnet[key].availability_zone
      cidr_block        = aws_subnet.subnet[key].cidr_block
    }
  }
}
output "vpc_id" {
  value       = aws_vpc.vpc.id
  description = "The AWS ID from the created VPC"
}

output "public_subnets" {
  value       = local.output_public_subnets
  description = "The ID and the availability zone of public subnets."
}

output "private_subnets" {
  description = "The ID and the availability zone of private subnets."
  value       = local.output_private_subnets
}