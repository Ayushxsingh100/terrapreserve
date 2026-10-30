
# OUTPUTS úteis
output "target_private_ip" {
  value = aws_instance.k8s_master.private_ip
}

output "target_public_ip" {
  value = aws_instance.k8s_master.public_ip
}

output "k8s_master_sg_id" {
  value = aws_security_group.k8s_master_sg.id
}
