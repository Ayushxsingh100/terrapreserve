output "public_subnets" {
  value = local.public_subnets
}

output "private_subnets" {
  value = local.private_subnets
}

output "vpc_id" {
  description = "The AWS ID from the created VPC"
  value       = aws_vpc.this.id
}

output "output_public_subnets" {
  description = "The ID and the AZ of privates"
  value       = local.output_public_subnets
}

output "output_private_subnets" {
  description = "The ID and the AZ of privates"
  value       = local.output_private_subnets
}