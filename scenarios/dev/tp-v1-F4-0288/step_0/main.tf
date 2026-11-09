locals {
  name = var.resource_tags
}

resource "aws_vpc" "labvpc" {
  cidr_block       = var.vpc_cidr
  instance_tenancy = "default"

  tags = local.name
}

resource "aws_subnet" "privatesubnet" {
  
  for_each = var.private_subnets

  vpc_id = aws_vpc.labvpc.id
  cidr_block = each.value

  tags = merge(local.name, {Name = each.key})
}

resource "aws_subnet" "publicsubnet" {
  
  for_each = var.public_subnets

  vpc_id = aws_vpc.labvpc.id
  cidr_block = each.value

  tags = merge(local.name, {Name = each.key})
}
