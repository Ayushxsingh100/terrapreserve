resource "aws_security_group" "rules" {
  for_each = var.security_group

  vpc_id = var.vpc_id
  name   = "${var.region_name}-sg-${each.key}"
  dynamic "ingress" {
    for_each = each.value.ingress_rules
    content {
      protocol  = ingress.value.protocol
      from_port = ingress.value.from_port
      to_port   = ingress.value.to_port
      cidr_blocks = ingress.value.cidr_blocks
    }
  }
  dynamic "egress" {
    for_each = each.value.egress_rules
    content {
      protocol  = egress.value.protocol
      from_port = egress.value.from_port
      to_port   = egress.value.to_port
      cidr_blocks = egress.value.cidr_blocks 
    }
  }
  tags = {
    Name = "${var.region_name}-sg-${each.key}"
  }
}
