resource "aws_security_group" "this" {
  count = var.create_security_group ? 1 : 0

  name        = var.name
  description = var.description
  vpc_id      = var.vpc_id

  lifecycle {
    ignore_changes        = [ingress, egress]
    create_before_destroy = true
  }

  tags = var.tags
}

resource "aws_security_group_rule" "ingress" {
  for_each = var.create_security_group ? { for idx, rule in var.ingress_rules : idx => rule } : {}

  security_group_id = aws_security_group.this[0].id
  type              = "ingress"
  from_port         = each.value.from_port
  to_port           = each.value.to_port
  protocol          = each.value.protocol
  cidr_blocks       = each.value.cidr_blocks
  description       = each.value.description
}

resource "aws_security_group_rule" "egress" {
  for_each = var.create_security_group ? { for idx, rule in var.egress_rules : idx => rule } : {}

  security_group_id = aws_security_group.this[0].id
  type              = "egress"
  from_port         = each.value.from_port
  to_port           = each.value.to_port
  protocol          = each.value.protocol
  cidr_blocks       = each.value.cidr_blocks
  description       = each.value.description
}
