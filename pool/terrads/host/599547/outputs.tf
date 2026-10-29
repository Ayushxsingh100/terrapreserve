output "public-ip-address" {
  value = aws_instance.test.public_ip
}