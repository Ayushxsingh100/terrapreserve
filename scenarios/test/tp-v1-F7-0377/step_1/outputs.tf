output "vpc_id" {
  value       = aws_vpc.main.id
  description = "The ID of the created VPC."
}

output "rtb_ids" {
  value = [
    aws_route_table.rtb_public.id
  ]
  description = "The IDs of all route tables"
}

output "public_subnets" {
  value = {
    for key, subnet in aws_subnet.public : key => {
      id = subnet.id
      az = subnet.availability_zone
    }
  }
  description = "Map of public subnet details by key"
}

output "igw_id" {
  value       = aws_internet_gateway.igw_main.id
  description = "The ID of the IGW"
}
