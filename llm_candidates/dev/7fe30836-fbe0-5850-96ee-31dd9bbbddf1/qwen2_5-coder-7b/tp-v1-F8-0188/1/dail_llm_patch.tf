resource "aws_security_group_rule" "service_access_deny_ssh" {
  type        = "ingress"
  from_port   = 22
  to_port     = 22
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0", "::/0"]
  security_group_id = aws_security_group.service_access.id
  description   = "Deny SSH from the entire IPv4 and IPv6 internet"
}
