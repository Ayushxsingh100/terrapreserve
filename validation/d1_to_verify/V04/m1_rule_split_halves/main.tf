resource "aws_security_group" "g" {
  name = "g"
}

resource "aws_security_group_rule" "r" {
  type              = "ingress"
  security_group_id = aws_security_group.g.id
  protocol          = "tcp"
  from_port         = 22
  to_port           = 22
  cidr_blocks       = ["0.0.0.0/1", "128.0.0.0/1"]
}
