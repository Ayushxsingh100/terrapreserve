resource "aws_security_group" "g" {
  name = "g"
}

resource "aws_vpc_security_group_egress_rule" "r" {
  security_group_id = aws_security_group.g.id
  ip_protocol       = "tcp"
  from_port         = 22
  to_port           = 22
  cidr_ipv4         = "0.0.0.0/0"
}
