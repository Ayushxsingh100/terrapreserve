resource "aws_security_group_rule" "data_secgroup_to_web_egress" {
  type = "egress"
  from_security_group_id = aws_security_group.web_secgroup.id
  ip_protocol = "-1"
  cidr_blocks = ["0.0.0.0/0"]
  description = "Allow egress to web_secgroup"
}

resource "aws_security_group_rule" "web_secgroup_no_ssh_ingress" {
  type = "ingress"
  from_port   = 22
  protocol    = "tcp"
  ip_protocol = "tcp"
  cidr_blocks = ["0.0.0.0/0", "::/0"]
  description = "Deny ingress on port 22 from all IPv4 and IPv6 addresses"
  rule_no = 100
}
