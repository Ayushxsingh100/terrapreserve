resource "aws_security_group_rule" "acme_app_sg_egress_db" {
  from_port                = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.acme_app_sg.id
  source_security_group_id = aws_security_group.acme_db_sg.id
  to_port                  = 5432
  type                     = "egress"
}

resource "aws_security_group" "acme_app_sg" {
  description = "Application security group for tpl-14"
  name        = "acme_app_sg-tpl-14"
  vpc_id      = aws_vpc.acme_vpc.id
}

resource "aws_instance" "acme_app" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.medium"
  subnet_id              = aws_subnet.acme_app_subnet.id
  vpc_security_group_ids = [aws_security_group.acme_app_sg.id]
}
