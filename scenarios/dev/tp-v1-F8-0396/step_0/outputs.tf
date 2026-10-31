output "ssh_connection" {
  value = "ssh -i ${var.ssh_key_path} ${var.ssh_user}@${aws_instance.minione.public_dns}"
  description = "SSH connection command"
}
