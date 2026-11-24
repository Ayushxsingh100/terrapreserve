resource "aws_security_group_rule" "tp_app_ingress_ssh_fixed" {
  type = "ingress"
  from_port   = 22
  to_port     = 22
  protocol    = "tcp"
  security_group_id = aws_security_group.tp_app_sg.id
  cidr_blocks = [aws_security_group.tp_app_sg.id]
}

resource "aws_security_group_rule" "tp_app_ingress_ssh_deleted" {
  type = "ingress"
  from_port   = 22
  to_port     = 22
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"]
  security_group_id = aws_security_group.tp_app_sg.id
}
