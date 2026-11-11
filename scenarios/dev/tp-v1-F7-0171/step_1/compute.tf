resource "aws_security_group_rule" "app_egress" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 1
  protocol          = "tcp"
  security_group_id = aws_security_group.app.id
  to_port           = 1023
  type              = "egress"
}

resource "aws_security_group" "app" {
  description = "Application security group for tpl-08"
  name        = "app-tpl-08"
  vpc_id      = aws_vpc.main.id
}

resource "aws_instance" "app" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.nano"
  subnet_id              = aws_subnet.app.id
  vpc_security_group_ids = [aws_security_group.app.id]
}
