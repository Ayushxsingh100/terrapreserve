# ----
# Security Group
# ----

resource "aws_security_group" "main" {
  count = var.enabled ? 1 : 0

  name        = var.name
  description = var.description
  vpc_id      = var.vpc_id

  dynamic "ingress" {
    for_each = var.ingress_rules
    content {
      description      = ingress.value.description
      from_port        = ingress.value.from_port
      to_port          = ingress.value.to_port
      protocol         = ingress.value.protocol
      cidr_blocks      = ingress.value.cidr_blocks
      ipv6_cidr_blocks = ingress.value.ipv6_cidr_blocks
      security_groups  = ingress.value.security_groups
      self             = ingress.value.self
    }
  }

  dynamic "ingress" {
    for_each = var.ingress_named_rules
    content {
      description      = var.named_rules[ingress.value.named_rule].description
      from_port        = var.named_rules[ingress.value.named_rule].from_port
      to_port          = var.named_rules[ingress.value.named_rule].to_port
      protocol         = var.named_rules[ingress.value.named_rule].protocol
      cidr_blocks      = ingress.value.cidr_blocks
      ipv6_cidr_blocks = ingress.value.ipv6_cidr_blocks
    }
  }

  dynamic "egress" {
    for_each = var.egress_rules
    content {
      description      = egress.value.description
      from_port        = egress.value.from_port
      to_port          = egress.value.to_port
      protocol         = egress.value.protocol
      cidr_blocks      = egress.value.cidr_blocks
      ipv6_cidr_blocks = egress.value.ipv6_cidr_blocks
      security_groups  = egress.value.security_groups
      self             = egress.value.self
    }
  }

  dynamic "egress" {
    for_each = var.egress_named_rules
    content {
      description      = var.named_rules[egress.value.named_rule].description
      from_port        = var.named_rules[egress.value.named_rule].from_port
      to_port          = var.named_rules[egress.value.named_rule].to_port
      protocol         = var.named_rules[egress.value.named_rule].protocol
      cidr_blocks      = egress.value.cidr_blocks
      ipv6_cidr_blocks = egress.value.ipv6_cidr_blocks
    }
  }

  tags = merge(
    var.tags,
    {
      Name                      = var.name
      "${var.networktags_name}" = var.networktags_value
    }
  )
}