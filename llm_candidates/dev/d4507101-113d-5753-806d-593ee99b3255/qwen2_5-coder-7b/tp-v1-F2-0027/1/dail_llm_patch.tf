resource "aws_security_group_rule" "data_secgroup_deny_ssh" {
  type              = "egress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0", "::/0"]
  security_group_id = aws_security_group.data_secgroup.id
}
