resource "aws_security_group_rule" "frontend_sg_ssh_denied" {
  type        = "ingress"
  from_port   = 22
  to_port     = 22
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0", "::/0"]
  security_group_id = aws_security_group.frontend_sg.id
  description   = "Deny public SSH access"
}
