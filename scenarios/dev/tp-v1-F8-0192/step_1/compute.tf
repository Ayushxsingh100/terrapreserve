resource "aws_security_group" "sg_app" {
  description = "Application security group for tpl-32"
  name        = "sg_app-tpl-32"
  vpc_id      = aws_vpc.vpc_main.id

  ingress {
    cidr_blocks = ["0.0.0.0/0"]
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

resource "aws_instance" "ec2_app" {
  ami                    = var.app_ami
  instance_type          = "t3.large"
  subnet_id              = aws_subnet.sub_app.id
  vpc_security_group_ids = [aws_security_group.sg_app.id]
}
