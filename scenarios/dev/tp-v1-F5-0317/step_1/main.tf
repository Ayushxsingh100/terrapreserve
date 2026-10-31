resource "aws_security_group" "main" {
  name        = var.sg_name
  description = var.sg_description
  vpc_id      = var.vpc_id

  dynamic "ingress" {
    for_each = var.ingress_ports
    content {
      description = lookup(ingress.value, "description", null)
      from_port   = ingress.value["from_port"]
      to_port     = ingress.value["to_port"]
      protocol    = lookup(ingress.value, "protocol", "tcp")
      cidr_blocks = ingress.value["cidr_blocks"]
    }
  }

  dynamic "egress" {
    for_each = var.egress_ports
    content {
      description = lookup(egress.value, "description", null)
      from_port   = egress.value["from_port"]
      to_port     = egress.value["to_port"]
      protocol    = lookup(egress.value, "protocol", "tcp")
      cidr_blocks = egress.value["cidr_blocks"]
    }
  }

  #   ingress {
  #     description      = "TLS from VPC"
  #     from_port        = 443
  #     to_port          = 443
  #     protocol         = "tcp"
  #     cidr_blocks      = [aws_vpc.main.cidr_block]
  #   }

  #   egress {
  #     from_port        = 0
  #     to_port          = 0
  #     protocol         = "-1"
  #     cidr_blocks      = ["0.0.0.0/0"]
  #     ipv6_cidr_blocks = ["::/0"]
  #   }

  tags = {
    Name = var.sg_name
  }
}