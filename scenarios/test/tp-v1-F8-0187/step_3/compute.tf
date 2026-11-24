resource "aws_security_group" "web" {
  description = "Application security group for tpl-12"
  name        = "web-tpl-12"
  vpc_id      = aws_vpc.net.id

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

resource "aws_security_group" "web_ops" {
  description = "Operations security group for tpl-12, attached to nothing"
  name        = "web_ops-tpl-12"
  vpc_id      = aws_vpc.net.id

  ingress {
    cidr_blocks = ["10.101.0.0/16"]
    from_port   = 443
    protocol    = "tcp"
    to_port     = 443
  }
}

resource "aws_instance" "web" {
  ami                    = local.app_ami
  instance_type          = "t3.large"
  subnet_id              = aws_subnet.pub.id
  vpc_security_group_ids = [aws_security_group.web.id]
}
