resource "aws_security_group_rule" "app_ssh_private" {
  from_port   = 22
  protocol    = "tcp"
  security_group_id = aws_security_group.app.id
  source_security_group_id = aws_security_group.app.id
  to_port     = 22
  type        = "ingress"
}
