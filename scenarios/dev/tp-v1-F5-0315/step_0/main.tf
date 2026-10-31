data "aws_security_group" "sg" {
    name = "test-sg"
}

resource "aws_security_group_rule" "dangerous-rules" {
  # for_each is unsupported
  for_each = toset(["22", "3389"])
  security_group_id = data.aws_security_group.sg.id
  description = "Port ${each.key} ingress"
  type = "ingress"
  from_port = each.key
  to_port = each.key
  protocol = "tcp"
  cidr_blocks = [ "0.0.0.0/0" ]
}
