resource "aws_security_group_rule" "allow_app_to_db_5432" {
  type = "ingress"
  from_port   = 5432
  protocol    = "tcp"
  to_port     = 5432
  security_group_id = aws_security_group.prod_db_sg.id
  cidr_blocks = [aws_security_group.prod_app_sg.id]
}
