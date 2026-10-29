output "sg_id" {
  value       = aws_security_group.worker_sg.id
  description = "The ID of the worker Security Group."
}

output "instance_id" {
  value       = aws_instance.worker.id
  description = "The ID of the worker EC2 instance."
}
