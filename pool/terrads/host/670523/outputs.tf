# 1. VPC ID
# 2. Public subnets - subnet_key => { subnet_id, availability_zone }
# 3. Private subnets - subnet_key => { subnet_id, availability_zone }

# Below locals block introduced in exercise 42
locals {
  output_public_subnets = {
    for key in keys(local.public_subnets) : key => {
      subnet_id         = aws_subnet.this[key].id
      availability_zone = aws_subnet.this[key].availability_zone
    }
  }

  output_private_subnets = {
    for key in keys(local.private_subnets) : key => {
      subnet_id         = aws_subnet.this[key].id
      availability_zone = aws_subnet.this[key].availability_zone
    }
  }


}


# Below introduced in excercise 41
# output "public_subnets" {
#   value = local.public_subnets
# }

# Below three output blocks introduced in exercise 42
output "vpc_id" {
  description = "The AWS VPC ID from the created VPC"
  value       = aws_vpc.this.id
}

output "public_subnets" {
  description = "The ID and the Availability zone of the public subnets"
  value       = local.output_public_subnets
}

output "private_subnets" {
  description = "The ID and the Availability zone of the private subnets"
  value       = local.output_private_subnets
}
