terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">=3.56"
		}
	}
}

resource "aws_security_group_rule" "group" {
	for_each          = var.services
  type              = "ingress"
  from_port         = 0
  to_port           = 65535
  protocol          = "tcp"
  cidr_blocks       = ["${each.value.node_address}/32"]
  description       = "security group rule added by CTS"
  security_group_id = var.security_group_id
}
