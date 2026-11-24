resource "aws_security_group_rule" "prod_app_sg_egress" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 0
  protocol          = "-1"
  security_group_id = aws_security_group.prod_app_sg.id
  to_port           = 0
  type              = "egress"
}

resource "aws_security_group" "prod_app_sg" {
  description = "Application security group for tpl-27"
  name        = "prod_app_sg-tpl-27"
  vpc_id      = aws_vpc.prod_vpc.id
}

resource "aws_instance" "prod_app_server" {
  ami                    = var.app_ami
  instance_type          = var.app_instance_type
  subnet_id              = aws_subnet.prod_app_subnet.id
  vpc_security_group_ids = [aws_security_group.prod_app_sg.id, aws_security_group.monitoring_sg.id]
}

resource "aws_security_group" "monitoring_sg" {
  description = "Monitoring security group"
  name        = "monitoring_sg-mon"
  vpc_id      = aws_vpc.prod_vpc.id

  ingress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 5432
    protocol    = "tcp"
    to_port     = 5432
  }
}
