output "K3S-SG" {
  description = "ID of the k3s cluster instance security group"
  value       = aws_security_group.k3s.id
}