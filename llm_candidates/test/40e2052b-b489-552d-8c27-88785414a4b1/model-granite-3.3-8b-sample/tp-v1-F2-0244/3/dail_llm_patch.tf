resource "aws_security_group_rule" "tp_app_ingress_postgres" {
  type = "ingress"
  from_port   = 5432
  to_port     = 5432
  protocol    = "tcp"
  cidr_blocks = ["10.0.0.0/16"]
  security_group_id = aws_security_group.tp_app_sg.id
}
