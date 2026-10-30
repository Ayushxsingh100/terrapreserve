resource "aws_security_group" "sg" {
  name    = join("-",[var.vpc_name,var.sg_name])
  vpc_id  = var.vpc_id

  egress {
    description = "All traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group_rule" "sg_rule" {
  count                    = length(var.sg_rules)
  security_group_id        = aws_security_group.sg.id
  type                     = "ingress"
  description              = lookup(var.sg_rules[count.index], "description","description not found")
  from_port                = lookup(var.sg_rules[count.index], "port","port not found")
  to_port                  = lookup(var.sg_rules[count.index], "port","port not found")
  protocol                 = lookup(var.sg_rules[count.index], "protocol","protocol not found")
  cidr_blocks              = lookup(var.sg_rules[count.index], "cidr","cidr not found") != "" ? [lookup(var.sg_rules[count.index], "cidr","cidr not found")] : null
  source_security_group_id = lookup(var.sg_rules[count.index], "sg_source","sg source not found") != "" ? lookup(var.sg_rules[count.index], "sg_source","sg source not found") : null
}

