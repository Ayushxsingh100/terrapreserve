output "instance_ids" {
  description = "IDs of the created EC2 instances"
  value       = aws_instance.web[*].id
}

output "security_group_id" {
  description = "ID of the created security group"
  value       = aws_security_group.ec2.id
}