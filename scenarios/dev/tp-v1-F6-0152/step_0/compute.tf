resource "aws_security_group_rule" "web_egress" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 0
  protocol          = "-1"
  security_group_id = aws_security_group.web.id
  to_port           = 0
  type              = "egress"
}

resource "aws_security_group" "web" {
  description = "Application security group for tpl-30"
  name        = "web-tpl-30"
  vpc_id      = aws_vpc.net.id
}

resource "aws_security_group" "web_ops" {
  description = "Operations security group for tpl-30, attached to nothing"
  name        = "web_ops-tpl-30"
  vpc_id      = aws_vpc.net.id

  ingress {
    cidr_blocks = ["10.168.0.0/16"]
    from_port   = 443
    protocol    = "tcp"
    to_port     = 443
  }
}

resource "aws_instance" "web" {
  ami                    = var.app_ami
  instance_type          = var.app_instance_type
  subnet_id              = aws_subnet.pub.id
  vpc_security_group_ids = [aws_security_group.web.id]
}
