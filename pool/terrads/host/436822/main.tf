terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "3.63.0"
    }
  }
}

provider "aws" {
  region  = "us-east-1"
  profile = "terraform"
}

resource "aws_instance" "this" {
  ami             = "ami-090fa75af13c156b4"
  instance_type   = "t2.micro"
  security_groups = [aws_security_group.this.name]
}

data "aws_vpc" "this" {
  state = "available"
  # id = "vpc-1ac55267"
}

locals {
  ingress = [
    {
      port        = 443
      description = "Port 443"
      protocol    = "tcp"
    },
    {
      port        = 80
      description = "Port 80"
      protocol    = "tcp"
    },
    {
      port        = 9090
      description = "Port 9090"
      protocol    = "tcp"
    }
  ]
}

resource "aws_security_group" "this" {
  name        = "sg_my_server"
  description = "Allow http inbound traffic"
  vpc_id      = data.aws_vpc.this.id


  dynamic "ingress" {
    for_each = local.ingress

    content {
      description      = ingress.value.description
      from_port        = ingress.value.port
      to_port          = ingress.value.port
      protocol         = ingress.value.protocol
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = []
      prefix_list_ids  = []
    }
  }

  egress {
    description      = "Outgoing traffic"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
    prefix_list_ids  = []
  }
}