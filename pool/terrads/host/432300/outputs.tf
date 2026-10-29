# Use Exiting VPC
output "vpc_id" {
  value = data.aws_vpc.default.id
}

output "subnet_ids" {
  value = [for s in data.aws_subnet.current : s.id]
}

output "subnet_cidr_blocks" {
  value = {
    for s in data.aws_subnet.current :
    s.id => s.cidr_block
  }
}

# output "subnet_cidr_block" {
#   value = data.aws_subnet.current.cidr_block
# }

# output "subnet_cidr_1" {
#   value = data.aws_subnet.current
# }

# output "subnet_cidr_2" {
#   value = data.aws_subnet.current[1].cidr_block
# }

# output "subnet_cidr_3" {
#   value = data.aws_subnet.current[2].cidr_block
# }

# output "vpc_id" {
#   value = aws_vpc.vpc.id
# }

output "public_sg" {
  value = aws_security_group.sg["public"].id
}

# output "public_subnet" {
#   value = aws_subnet.public_subnet.id
# }
