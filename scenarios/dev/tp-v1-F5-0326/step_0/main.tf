locals {
  create_this = var.create_this
}

################################################################################
# Security Group
################################################################################

resource "aws_security_group" "this" {
  count = local.create_this ? 1 : 0

  vpc_id      = var.vpc_id
  description = var.description
  dynamic "egress" {
    for_each = var.egresses
    content {
      from_port        = egress.value["from_port"]
      to_port          = egress.value["to_port"]
      cidr_blocks      = egress.value["cidr_blocks"]
      description      = egress.value["description"]
      ipv6_cidr_blocks = egress.value["ipv6_cidr_blocks"]
      prefix_list_ids  = egress.value["prefix_list_ids"]
      protocol         = egress.value["protocol"]
      security_groups  = egress.value["security_groups"]
      self             = egress.value["self"]
    }
  }
  dynamic "ingress" {
    for_each = var.ingresses
    content {
      from_port        = ingress.value["from_port"]
      to_port          = ingress.value["to_port"]
      protocol         = ingress.value["protocol"]
      cidr_blocks      = ingress.value["cidr_blocks"]
      description      = ingress.value["description"]
      ipv6_cidr_blocks = ingress.value["ipv6_cidr_blocks"]
      prefix_list_ids  = ingress.value["prefix_list_ids"]
      security_groups  = ingress.value["security_groups"]
      self             = ingress.value["self"]
    }
  }
  name_prefix            = var.name_prefix
  name                   = var.name
  revoke_rules_on_delete = var.revoke_rules_on_delete

  tags = merge(
    { "Name" = var.name },
    var.tags,
  )
}