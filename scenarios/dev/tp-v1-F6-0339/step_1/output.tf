output "sg_id_web_servers" {
  description = "Web servers Security Group ID"
  value       = aws_security_group.web_servers.id
}

output "sg_id_load_balancers" {
  description = "Load balancers Security Group ID"
  value       = aws_security_group.load_balancers.id
}