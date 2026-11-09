resource "aws_security_group" "sig_sg" {
  name        = "${var.stack_name}-${var.env}-${var.aws_region}-${var.stack_tool}-sg"
  description = "SIG security group"
  vpc_id      = var.vpc_id

  dynamic "ingress" {
    for_each = var.ingress_rules
    iterator = each

    content {
      description      = each.value.description
      from_port        = each.value.from_port
      to_port          = each.value.to_port
      protocol         = each.value.protocol
      cidr_blocks      = each.value.cidr_blocks
      ipv6_cidr_blocks = each.value.ipv6_cidr_blocks
      security_groups = each.value.security_groups
    }
  }

  dynamic "egress" {
    for_each = var.egress_rules
    iterator = each

    content {
      description      = each.value.description
      from_port        = each.value.from_port
      to_port          = each.value.to_port
      protocol         = each.value.protocol
      cidr_blocks      = each.value.cidr_blocks
      ipv6_cidr_blocks = each.value.ipv6_cidr_blocks
    }
  }

  tags = {
    Name = "${var.stack_name}-${var.env}-${var.aws_region}-${var.stack_tool}-sg"
    Environment = terraform.workspace
  }
}