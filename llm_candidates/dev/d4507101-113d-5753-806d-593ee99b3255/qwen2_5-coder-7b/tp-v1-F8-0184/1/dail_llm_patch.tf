resource "aws_security_group_rule" "prod_app_sg_deny_ssh" {
  type        = "ingress"
  from_port   = 22
  to_port     = 22
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0", "::/0"]
  security_group_id = aws_security_group.prod_app_sg.id
  description   = "Deny SSH from the entire internet"
}
