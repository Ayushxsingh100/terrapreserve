resource "aws_instance" "bastion" {
  ami           = var.instance_ami
  instance_type = var.instance_type
  subnet_id     = var.public_subnet_id
  security_groups = [aws_security_group.bastion.id]

  tags = {
    Name = "Bastion Host"
  }
}

resource "aws_security_group" "bastion" {
  vpc_id = var.vpc_id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
