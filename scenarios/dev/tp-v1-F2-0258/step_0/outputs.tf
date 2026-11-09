output "vpc_id" {

  description = "The ID of the VPC"
  value       = aws_vpc.this.id
  # providing the output for the vpc_id
}

output "public_subnets" {

  description = "The ID of the Public Subnets"
  value = {
    for key, value in aws_subnet.this :
    key => {
      id = value.id
      az = value.availability_zone
    }
    if can(aws_route_table.this[key])
  }
  # providing the output for the public_subnets
}

output "private_subnets" {

  description = "The ID of the private Subnets"
  value = {
    for key, value in aws_subnet.this :
    key => {
      id = value.id
      az = value.availability_zone
    }
    if !can(aws_route_table.this[key])
  }
  # providing the output for the private_subnets
}