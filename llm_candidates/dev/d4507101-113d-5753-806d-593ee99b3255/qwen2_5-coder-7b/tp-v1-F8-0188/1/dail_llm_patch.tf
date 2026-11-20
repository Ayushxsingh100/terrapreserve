resource "aws_security_group_rule" "deny_ssh_inbound" {
  type        = "ingress"
  from_port   = 22
  to_port     = 22
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0", "::/0"]
  security_group_id = aws_security_group.service_access.id
  description = "Deny SSH inbound from the entire IPv4 and IPv6 internet"
}
