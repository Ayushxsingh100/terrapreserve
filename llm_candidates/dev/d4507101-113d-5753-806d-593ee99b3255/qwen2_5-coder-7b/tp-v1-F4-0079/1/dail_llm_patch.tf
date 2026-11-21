resource "aws_security_group_rule" "app_ssh_private" {
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0", "::/0"]
  security_group_id = aws_security_group.app.id
  description       = "Deny SSH ingress from the entire IPv4 and IPv6 internet"
}
