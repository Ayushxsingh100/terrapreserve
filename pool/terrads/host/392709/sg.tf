resource "aws_security_group" "cidr_sg" {
  count       = length(var.cidr_sg)
  vpc_id      = var.vpc_id
  dynamic "ingress" {
    for_each = var.cidr_sg[count.index]["ingress"]
    content {
          from_port       = ingress.value["from_port"]
          to_port         = ingress.value["to_port"]
          protocol        = ingress.value["protocol"]
          cidr_blocks     = ingress.value["cidr"]
          self            = ingress.value["self"] == "" ? null : true
        }
    }

  dynamic "egress" {
    for_each = var.cidr_sg[count.index]["egress"]
    content {
          from_port       = egress.value["from_port"]
          to_port         = egress.value["to_port"]
          protocol        = egress.value["protocol"]
          cidr_blocks     = egress.value["cidr"]
          self            = egress.value["self"] == "" ? null : true
        }
    }

  tags = {
      Name = element(var.cidr_sg_name, count.index)
  }
}

resource "aws_security_group" "my_sg" {
  count       = length(var.sg) > 1 ? length(var.sg) : 0
  vpc_id      = var.vpc_id
  dynamic "ingress" {
    for_each = var.sg[count.index]["ingress"]
    content {
          from_port       = ingress.value["from_port"]
          to_port         = ingress.value["to_port"]
          protocol        = ingress.value["protocol"]
          security_groups = ingress.value["self"] == true ? null : ingress.value["sg"]
          self            = ingress.value["self"] == "" ? null : true
        }
    }

  dynamic "egress" {
    for_each = var.sg[count.index]["egress"]
    content {
          from_port       = egress.value["from_port"]
          to_port         = egress.value["to_port"]
          protocol        = egress.value["protocol"]
          security_groups = egress.value["self"] == true ? null : egress.value["sg"]
          self            = egress.value["self"] == "" ? null : true
        }
    }

  tags = {
      Name = element(var.sg_name, count.index)
  }
}
