output "public_subnet_ids" {
  description = "IDs of created public subnets"
  value       = aws_subnet.public[*].id
}
output "private_subnet_ids" {
  description = "IDs of created private subnets"
  value       = aws_subnet.private[*].id
}