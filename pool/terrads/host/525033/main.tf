terraform {
  required_version = ">= 1.0.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.22"
    }
  }
}

locals {
  aa_egresses = [
    {
      from_port          = 0
      to_port            = 0
      protocol           = "-1"
      cidr_blocks        = ["0.0.0.0/0"]
      ipv6_cidr_blocks   = null
      security_group_ids = null
    },
    {
      from_port          = 0
      to_port            = 0
      protocol           = "-1"
      cidr_blocks        = null
      ipv6_cidr_blocks   = ["::/0"]
      security_group_ids = null
    }
  ]
  egresses = var.egress_allow_all ? local.aa_egresses : toset(var.egress_rules)
}

resource "aws_security_group" "this" {
  name        = var.name
  description = var.description
  tags        = var.tags
  vpc_id      = var.default_vpc_id
  dynamic "ingress" {
    for_each = var.ingress_rules
    content {
      from_port        = ingress.value["from_port"]
      to_port          = ingress.value["to_port"]
      protocol         = ingress.value["protocol"]
      cidr_blocks      = ingress.value["cidr_blocks"]
      ipv6_cidr_blocks = ingress.value["ipv6_cidr_blocks"]
      security_groups  = ingress.value["security_group_ids"]
    }
  }
  dynamic "egress" {
    for_each = local.egresses
    content {
      from_port        = egress.value["from_port"]
      to_port          = egress.value["to_port"]
      protocol         = egress.value["protocol"]
      cidr_blocks      = egress.value["cidr_blocks"]
      ipv6_cidr_blocks = egress.value["ipv6_cidr_blocks"]
      security_groups  = egress.value["security_group_ids"]
    }
  }
}
