output "subnet_config" {
  value = var.subnet_config
}

output "subnets" {
  value = aws_subnet.main
}
