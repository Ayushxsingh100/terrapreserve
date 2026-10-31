resource "aws_security_group" "web_servers" {

  name        = "web-servers"
  description = "Allow traffic for web servers"
  vpc_id      = var.vpc_id

  ingress {

    description     = "Allow traffic from load balancer"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.load_balancers.id]
  }

  dynamic "ingress" {
    for_each = var.is_web_sg_ingress ? { for i, v in var.web_sg_ingress : i => v } : {}

    content {
      description = ingress.value.description
      from_port   = ingress.value.from_port
      to_port     = ingress.value.to_port
      protocol    = ingress.value.protocol
      cidr_blocks = ingress.value.cidrs

    }
  }

  dynamic "egress" {
    for_each = var.is_lb_sg_egress ? { for i, v in var.lb_sg_egress : i => v } : {}

    content {
      description = egress.value.description
      from_port   = egress.value.from_port
      to_port     = egress.value.to_port
      protocol    = egress.value.protocol
      cidr_blocks = egress.value.cidrs

    }
  }

  tags = {
    Name        = "web-servers"
    Description = "Allow traffic for web servers"
  }
}

resource "aws_security_group" "load_balancers" {

  name        = "load-balancers"
  description = "Allow traffic for load balancers"
  vpc_id      = var.vpc_id

  dynamic "ingress" {
    for_each = var.is_lb_sg_ingress ? { for i, v in var.lb_sg_ingress : i => v } : {}

    content {
      description = ingress.value.description
      from_port   = ingress.value.from_port
      to_port     = ingress.value.to_port
      protocol    = ingress.value.protocol
      cidr_blocks = ingress.value.cidrs

    }
  }
  dynamic "egress" {
    for_each = var.is_lb_sg_egress ? { for i, v in var.lb_sg_egress : i => v } : {}

    content {
      description = egress.value.description
      from_port   = egress.value.from_port
      to_port     = egress.value.to_port
      protocol    = egress.value.protocol
      cidr_blocks = egress.value.cidrs

    }
  }

  tags = {
    Name        = "load-balancers"
    Description = "Allow traffic for load balancers"
  }
}