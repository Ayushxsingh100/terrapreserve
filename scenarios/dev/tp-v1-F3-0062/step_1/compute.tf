resource "aws_security_group" "sg_app" {
  description = "Application security group for tpl-32"
  name        = "sg_app-tpl-32"
  vpc_id      = aws_vpc.vpc_main.id

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_instance" "ec2_app" {
  ami                    = var.app_ami
  instance_type          = var.app_instance_type
  subnet_id              = aws_subnet.sub_app.id
  vpc_security_group_ids = [aws_security_group.sg_app.id]
}

resource "aws_security_group" "sg_db_peer" {
  description = "Dependent client security group"
  name        = "sg_db-tpl-32-peer"
  vpc_id      = aws_vpc.vpc_main.id
}
