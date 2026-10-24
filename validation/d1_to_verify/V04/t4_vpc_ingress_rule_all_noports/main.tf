resource "aws_security_group" "g" {
  name = "g"
}

resource "aws_vpc_security_group_ingress_rule" "r" {
  security_group_id = aws_security_group.g.id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}
