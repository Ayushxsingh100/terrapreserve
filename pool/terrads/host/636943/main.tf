resource "aws_security_group" "dev_sg" {
  name        = var.name
  description = var.description
  vpc_id      = var.vpc_id

  dynamic "ingress" {
    for_each = var.ingress_rules
    content {
      from_port   = ingress.value.from_port
      to_port     = ingress.value.to_port
      protocol    = ingress.value.protocol
      description = ingress.value.description

      # Only include cidr_blocks if provided
      cidr_blocks = lookup(ingress.value, "cidr_blocks", [])

      # Only include security_groups if provided
      security_groups = lookup(ingress.value, "source_security_group_id", null) != null ? [ingress.value.source_security_group_id] : null
    }
  }

  dynamic "egress" {
    for_each = var.egress_rules
    content {
      from_port   = egress.value.from_port
      to_port     = egress.value.to_port
      protocol    = egress.value.protocol
      cidr_blocks = egress.value.cidr_blocks
      description = egress.value.description
    }
  }

  tags = var.tags
}
