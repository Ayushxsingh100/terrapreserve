output "vpc" {
    description = "The ID of the VPC"
    value       = aws_vpc.vpc.id
}

output "igw" {
    description = "The ID of the Internet Gateway"
    value       = aws_internet_gateway.igw.id
}

output "subnet_az_a" {
    description = "The ID of the subnet in availability zone A"
    value       = aws_subnet.subnet_a.id
}

output "subnet_az_b" {
    description = "The ID of the subnet in availability zone B"
    value       = aws_subnet.subnet_b.id
}