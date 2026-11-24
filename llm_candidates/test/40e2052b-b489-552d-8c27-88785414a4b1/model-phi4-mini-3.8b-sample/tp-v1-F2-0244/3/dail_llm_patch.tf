resource "aws_security_group_rule" "tp_app_ingress_postgres" {
  description = "Allow PostgreSQL ingress from the entire IPv4 internet"
  security_group_id = aws_security_group.tp_db_sg.id
  type = "ingress"
  from_port = 5432
  protocol = "tcp"
  to_port = 5432
  cidr_blocks = ["0.0.0.0/0"]
}
