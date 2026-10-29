output "vpc_id" {
  description = "The ID of the VPC"
  value       = aws_vpc.this.id
}

# Expose the subnet IDs so the EC2 example can use them
output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = [for s in aws_subnet.public : s.id]
}