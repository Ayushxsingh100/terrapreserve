terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = " ~> 3.0"
    }
  }
}


provider "aws" {
  region = "eu-central-1"
}

locals {
  cidrs = ["10.0.0.0/8","172.16.0.0/12"]
  ports = [22, 3389, 80, 433, 8080]
}


resource "aws_security_group" "allow_tls" {
  name        = "Allow-app-traffic"
  description = "Allow app inbound traffic"
  #vpc_id      = aws_vpc.main.id

  dynamic "ingress" {
      for_each = local.ports
      content {
            description      = "allow ${ingress.value}"
            from_port        = ingress.value
            to_port          = ingress.value
            protocol         = "tcp"
            cidr_blocks      = local.cidrs
            ipv6_cidr_blocks = []
      }
  }

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "Dynamic bloks SG"
  }
}