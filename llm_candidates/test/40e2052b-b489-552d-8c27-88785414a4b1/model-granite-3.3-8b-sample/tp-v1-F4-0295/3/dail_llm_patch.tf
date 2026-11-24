resource "aws_security_group_rule" "tp_db_egress" {
  type = "egress"
  from_port = 0
  to_port = 0
  protocol = "-1"
  cidr_blocks = ["0.0.0.0/0"]
  security_group_id = aws_security_group.tp_db_sg.id
}

resource "aws_security_group_rule" "tp_db_ingress_app" {
  type = "ingress"
  from_port   = 5432
  to_port     = 5432
  protocol    = "tcp"
  cidr_blocks = [
    aws_security_group.tp_app_sg.id
  ]
  security_group_id = aws_security_group.tp_db_sg.id
}
