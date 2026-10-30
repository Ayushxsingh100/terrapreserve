output "id" {
  description = "The ID of the created instance"
  value       = aws_instance.server.id
}

output "public_ip" {
  description = "The public IP address of the instance"
  value       = try(aws_instance.server.public_ip, null)
}

output "private_ip" {
  description = "The private IP address of the instance"
  value       = aws_instance.server.private_ip
}

output "type" {
  description = "The type of instance deployed"
  value       = aws_instance.server.instance_type
}

output "name" {
  description = "The name of the instance"
  value       = aws_instance.server.tags.Name
}