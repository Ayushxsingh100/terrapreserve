resource "aws_security_group_rule" "app_ingress_db_5432" {
  type = "ingress"
  from_port   = 5432
  to_port     = 5432
  protocol    = "tcp"
  security_group_id = aws_security_group.tp_app_sg.id
  cidr_blocks = [aws_security_group.tp_db_sg.id]
}

resource "aws_security_group_rule" "db_ingress_postgres_restricted" {
  type = "ingress"
  from_port   = 5432
  to_port     = 5432
  protocol    = "tcp"
  security_group_id = aws_security_group.tp_db_sg.id
  cidr_blocks = [
    aws_security_group.tp_app_sg.id,
    aws_instance.tp_app.public_ip,
  ]
}

resource "aws_security_group_rule" "db_egress_all" {
  type = "egress"
  from_port   = 0
  to_port     = 0
  protocol    = "-1"
  security_group_id = aws_security_group.tp_db_sg.id
  cidr_blocks = ["0.0.0.0/0"]
}

resource "aws_security_group_rule" "db_egress_specific" {
  type = "egress"
  from_port   = 5432
  to_port     = 5432
  protocol    = "tcp"
  security_group_id = aws_security_group.tp_db_sg.id
  cidr_blocks = [
    aws_security_group.tp_app_sg.id,
    aws_instance.tp_app.public_ip,
  ]
}
