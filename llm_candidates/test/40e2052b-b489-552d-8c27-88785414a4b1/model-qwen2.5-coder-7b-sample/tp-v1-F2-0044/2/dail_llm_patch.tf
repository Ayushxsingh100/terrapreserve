resource "aws_security_group_rule" "db_egress_deny" {
  from_port   = 0
  to_port     = 0
  protocol    = "-1"
  cidr_blocks = ["0.0.0.0/0"]
  security_group_id = aws_security_group.db.id
  type        = "egress"
  description = "Deny all outbound traffic from the database security group"
}
