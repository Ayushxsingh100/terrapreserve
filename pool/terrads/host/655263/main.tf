resource "aws_security_group" "this" {
  vpc_id = var.vpc_id
  name   = "allow-ssh"

  ingress {
    description = "Allow SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidr
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "allow-ssh" })
}

output "sg_id" {
  value = aws_security_group.this.id
}
