locals {
  l1_map = {
    for k_vpc, v_vpc in var.vpc_map : k_vpc => merge(v_vpc, {
      security_group_map = {
        for k_sg, v_sg in v_vpc.security_group_map : replace(k_sg, "/[-]/", "_") => merge(v_sg, {
          k_sg_full = replace("${k_vpc}-${k_sg}", var.std_map.name_replace_regex, "-")
          name      = replace(k_sg, var.std_map.name_replace_regex, "-")
          rule_map = {
            for k_rule, v_rule in v_sg.rule_map : replace(k_rule, var.std_map.name_replace_regex, "-") => merge(v_rule, {
              has_source  = v_rule.source_is_self != null || v_rule.source_security_group_id != null
              k_rule_full = replace("${k_vpc}-${k_sg}-${k_rule}", var.std_map.name_replace_regex, "-")
            })
          }
        })
      }
    })
  }
  l2_map = {
    for k_vpc, _ in var.vpc_map : k_vpc => {
      security_group_map = {
        for k_sg, v_sg in local.l1_map[k_vpc].security_group_map : k_sg => merge(v_sg, {
          name_context = "${var.std_map.resource_name_prefix}${local.l1_map[k_vpc].name_simple}-${v_sg.name}${var.std_map.resource_name_suffix}"
          rule_map = {
            for k_rule, v_rule in v_sg.rule_map : k_rule => merge(v_rule, {
              cidr_blocks      = v_rule.has_source ? null : v_rule.cidr_blocks
              ipv6_cidr_blocks = v_rule.has_source ? null : v_rule.ipv6_cidr_blocks
            })
          }
        })
      }
    }
  }
  l3_map = {
    for k_vpc, _ in var.vpc_map : k_vpc => {
      security_group_map = {
        for k_sg, v_sg in local.l2_map[k_vpc].security_group_map : k_sg => merge(v_sg, {
          name_effective = v_sg.name_context
          tags = merge(
            var.std_map.tags,
            {
              Name = v_sg.name_context
            }
          )
        })
      }
    }
  }
  output_data = {
    for k_vpc, v_vpc in local.vpc_map : k_vpc => {
      security_group_id_map = {
        for k_sg, v_sg in v_vpc.security_group_map : k_sg => aws_security_group.this_sg[v_sg.k_sg_full].id
      }
      security_group_map = {
        for k_sg, v_sg in v_vpc.security_group_map : k_sg => merge(v_sg, {
          id = aws_security_group.this_sg[v_sg.k_sg_full].id
        })
      }
    }
  }
  sg_flattened_list = flatten([
    for k_vpc, v_vpc in local.vpc_map : flatten([
      for k_sg, v_sg in v_vpc.security_group_map : merge(v_vpc, v_sg)
    ])
  ])
  sg_flattened_map = {
    for v_sg in local.sg_flattened_list : v_sg.k_sg_full => v_sg
  }
  sg_rule_flattened_list = flatten([
    for v_sg in local.sg_flattened_list : [
      for k_rule, v_rule in v_sg.rule_map : merge(v_sg, v_rule)
    ]
  ])
  sg_rule_flattened_map = {
    for v_rule in local.sg_rule_flattened_list : v_rule.k_rule_full => v_rule
  }
  vpc_map = {
    for k_vpc, _ in var.vpc_map : k_vpc => merge(local.l1_map[k_vpc], local.l2_map[k_vpc], local.l3_map[k_vpc])
  }
}
