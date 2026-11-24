resource "aws_security_group" "app" {
  description = "Application security group for tpl-17"
  name        = "app-tpl-17"
  vpc_id      = aws_vpc.main.id

  ingress {
    cidr_blocks = ["10.0.0.0/8"]
    from_port   = 22
    protocol    = "tcp"
    to_port     = 22
  }

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_security_group" "app_ops" {
  description = "Operations security group for tpl-17, attached to nothing"
  name        = "app_ops-tpl-17"
  vpc_id      = aws_vpc.main.id

  ingress {
    cidr_blocks = ["10.69.0.0/16"]
    from_port   = 443
    protocol    = "tcp"
    to_port     = 443
  }
}

resource "aws_instance" "app" {
  ami                    = var.app_ami
  instance_type          = "t3.large"
  subnet_id              = aws_subnet.app.id
  vpc_security_group_ids = [aws_security_group.app.id]
}
