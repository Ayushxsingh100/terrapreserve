output "subnetId" {
  description = "ID of the Subnet"
  value       = aws_subnet.spacelift_public_subnet.id
}

output "spacelift_sg" {
  value = aws_security_group.allow_access.id
}
