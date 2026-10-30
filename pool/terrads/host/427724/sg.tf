resource "aws_security_group" "db" {
  name   = "${var.identifier_prefix}-db"
  vpc_id = var.vpc_id
}

resource "aws_security_group_rule" "allow_inbound" {
  type                     = "ingress"
  security_group_id        = aws_security_group.db.id
  source_security_group_id = var.security_group_id

  from_port   = var.db_port
  to_port     = var.db_port
  protocol    = "tcp"
}
resource "aws_security_group_rule" "allow_all_outbound" {
  type              = "egress"
  security_group_id = aws_security_group.db.id

  from_port   = 0
  to_port     = 0
  protocol    = "-1"
  cidr_blocks = ["0.0.0.0/0"]
}
