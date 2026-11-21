resource "aws_security_group_rule" "service_access_allow_ssh" {
  type = "ingress"
  description = "Allow SSH access from service_access group"
  security_group_id = aws_security_group.service_access.id
  rule_description = "SSH access from service group"
  protocol = "tcp"
  from_port = 22
  to_port = 22
}
