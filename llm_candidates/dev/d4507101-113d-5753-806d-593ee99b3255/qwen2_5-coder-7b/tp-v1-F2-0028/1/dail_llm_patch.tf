resource "aws_security_group_rule" "acme_db_sg_no_public_5432" {
  type              = "ingress"
  from_port         = 5432
  to_port           = 5432
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0", "::/0"]
  security_group_id = aws_security_group.acme_db_sg.id
  description       = "Deny public PostgreSQL ingress"
}
