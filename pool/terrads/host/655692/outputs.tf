# Security Groups Module Outputs

output "ssh_sg_id" {
  description = "ID of the SSH security group"
  value       = aws_security_group.ssh.id
}

output "nomad_server_sg_id" {
  description = "ID of the Nomad server security group"
  value       = aws_security_group.nomad_server.id
}

output "nomad_client_sg_id" {
  description = "ID of the Nomad client security group"
  value       = aws_security_group.nomad_client.id
}

output "alb_sg_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb.id
}
