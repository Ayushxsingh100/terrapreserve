########################################################################################################################
# Define variables
########################################################################################################################
# variable "vpc_id" {}
variable "set_username_prefix" {}
variable "set_alb_sg_name" {}
variable "set_alb_sg_description" {}
variable "set_alb_sg_ingress_rules" {}
variable "set_alb_sg_egress_rules" {}
variable "set_ecs_sg_name" {}
variable "set_ecs_sg_description" {}
variable "set_ecs_sg_egress_rules" {}

########################################################################################################################
# Create resources
########################################################################################################################
data "aws_vpc" "vpc_id" {
  filter {
    name   = "tag:Name"
    values = ["${var.set_username_prefix}"]
  }
}

resource "aws_security_group" "alb_sg" {
  name        = "${var.set_username_prefix}-${var.set_alb_sg_name}"
  description = var.set_alb_sg_description
  vpc_id      = data.aws_vpc.vpc_id.id

  dynamic "ingress" {
    for_each = var.set_alb_sg_ingress_rules
    content {
      from_port   = ingress.value.from
      to_port     = ingress.value.to
      protocol    = ingress.value.protocol
      cidr_blocks = ingress.value.cidr
    }
  }

  dynamic "egress" {
    for_each = var.set_alb_sg_egress_rules
    content {
      from_port   = egress.value.from
      to_port     = egress.value.to
      protocol    = egress.value.protocol
      cidr_blocks = egress.value.cidr
    }
  }
  tags = {
    Name = "${var.set_username_prefix}-${var.set_alb_sg_name}"
  }
}

resource "aws_security_group" "ecs_sg" {
  name        = "${var.set_username_prefix}-${var.set_ecs_sg_name}"
  description = var.set_ecs_sg_description
  vpc_id      = data.aws_vpc.vpc_id.id

  ingress {
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  dynamic "egress" {
    for_each = var.set_ecs_sg_egress_rules
    content {
      from_port   = egress.value.from
      to_port     = egress.value.to
      protocol    = egress.value.protocol
      cidr_blocks = egress.value.cidr
    }
  }
  tags = {
    Name = "${var.set_username_prefix}-${var.set_ecs_sg_name}"
  }
}

########################################################################################################################
# Define outputs
########################################################################################################################
output "alb_sg_id" {
  description = "The ID of the security group"
  value       = aws_security_group.alb_sg.id
}

output "ecs_sg_id" {
  description = "The ID of the security group"
  value       = aws_security_group.ecs_sg.id
}
