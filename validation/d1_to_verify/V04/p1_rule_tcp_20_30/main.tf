resource "aws_security_group" "g" {
  name = "g"
}

resource "aws_security_group_rule" "r" {
  type              = "ingress"
  security_group_id = aws_security_group.g.id
  protocol          = "tcp"
  from_port         = 20
  to_port           = 30
  cidr_blocks       = ["0.0.0.0/0"]
}
