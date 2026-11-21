resource "aws_security_group" "service_access-tpl-16" {
  ingress = [{
    description = "Allow SSH access from anywhere",
    from_port = 22,
    to_port = 22,
    protocol = "tcp",
    cidr_blocks = ["0.0.0.0/0"]
  }]
}
