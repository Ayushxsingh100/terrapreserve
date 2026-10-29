output "vpc_id" {
  description = "The ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "The CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "The IDs of the public subnets"
  value       = [for key, subnet in local.public_subnet : aws_subnet.main[key].id]
}

output "private_subnet_ids" {
  description = "The IDs of the private subnets"
  value       = [for key, subnet in local.private_subnet : aws_subnet.main[key].id]
}

output "vpc_name" {
  description = "The name of the VPC"
  value       = aws_vpc.main.tags["Name"]
}

output "internet_gateway_id" {
  description = "The ID of the Internet Gateway, if created"
  value       = aws_internet_gateway.main[0].id
}

output "route_table_id" {
  description = "The ID of the route table for the public subnets, if created"
  value       = aws_route_table.main[0].id
}
