resource "aws_security_group" "security_group_https_ssh" {
  name = var.security_group_name
  vpc_id = var.vpc_id
  tags = {
    Name = var.security_group_name
  }
  ingress {
    description = "HTTPS"
    from_port = 443
    protocol  = "tcp"
    to_port   = 443
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "SSH"
    from_port = 22
    protocol  = "tcp"
    to_port   = 22
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All access"
    from_port = 0
    protocol  = "-1"
    to_port   = 0
    cidr_blocks = ["0.0.0.0/0"]
  }
}