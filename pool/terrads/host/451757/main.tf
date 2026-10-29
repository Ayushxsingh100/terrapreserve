resource "aws_security_group" "this_sg" {
  for_each = local.sg_flattened_map
  # egress # Deprecated
  # ingress # Deprecated
  name = each.value.name_effective
  # name_prefix # Conflicts with name
  region                 = var.std_map.aws_region_name
  revoke_rules_on_delete = each.value.revoke_rules_on_delete
  tags                   = each.value.tags
  vpc_id                 = each.value.vpc_id
}

resource "aws_security_group_rule" "this_sg_rule" {
  for_each                 = local.sg_rule_flattened_map
  cidr_blocks              = each.value.cidr_blocks
  from_port                = each.value.from_port
  ipv6_cidr_blocks         = each.value.ipv6_cidr_blocks
  prefix_list_ids          = each.value.prefix_id_list
  protocol                 = each.value.protocol
  region                   = var.std_map.aws_region_name
  security_group_id        = aws_security_group.this_sg[each.value.k_sg_full].id
  self                     = each.value.source_is_self
  source_security_group_id = each.value.source_security_group_id
  to_port                  = each.value.to_port
  type                     = each.value.type
}
