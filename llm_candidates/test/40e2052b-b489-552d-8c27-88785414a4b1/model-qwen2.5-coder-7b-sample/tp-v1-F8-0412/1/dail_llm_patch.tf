resource "aws_security_group_rule" "tp_app_ingress_ssh_restricted" {
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = []
  ipv6_cidr_blocks  = []
  security_group_id = aws_security_group.tp_app_sg.id
}
