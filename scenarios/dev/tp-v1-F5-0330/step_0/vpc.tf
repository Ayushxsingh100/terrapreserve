locals {
  subnets = cidrsubnets(var.cidr_block, var.subnets[*].new_bits...)
  subnets_with_cidr = [for i, n in var.subnets : {
    name       = n.name
    az         = n.az
    cidr_block = n.name != null ? local.subnets[i] : tostring(null)
  }]
  subnt_map = { for s in local.subnets_with_cidr : s.name => { az = s.az, cidr_block = s.cidr_block } }
  private_subnet_ids = {
    for val in aws_subnet.main : val.tags.Name => {
      subnet_id = val.id
    }
    if !can(regex("^Public Subnet [[:digit:]]", val.tags.Name))
  }
  az_1_private_subnets = [
    for k, val in local.private_subnet_ids : val.subnet_id
    if can(regex("[[:alpha:]]+ [[:alpha:]]+ 1$", k))
  ]
  route_az1_map = { tostring(local.public_subnet_ids["Public Subnet 1"]["subnet_id"]) = local.az_1_private_subnets }
  az_2_private_subnets = [
    for k, val in local.private_subnet_ids : val.subnet_id
    if can(regex("[[:alpha:]]+ [[:alpha:]]+ 2$", k))
  ]
  route_az2_map = { tostring(local.public_subnet_ids["Public Subnet 2"]["subnet_id"]) = local.az_2_private_subnets }
  az_3_private_subnets = [
    for k, val in local.private_subnet_ids : val.subnet_id
    if can(regex("[[:alpha:]]+ [[:alpha:]]+ 3$", k))
  ]
  route_az3_map = { tostring(local.public_subnet_ids["Public Subnet 3"]["subnet_id"]) = local.az_3_private_subnets }
  public_subnet_ids = {
    for val in aws_subnet.main : val.tags.Name => {
      subnet_id = val.id
    }
    if can(regex("^Public Subnet [[:digit:]]", val.tags.Name))
  }
}

resource "aws_vpc" "main" {
  cidr_block           = var.cidr_block
  enable_dns_support   = var.enable_dns_support
  enable_dns_hostnames = var.enable_dns_hostnames
  tags                 = merge({ "Name" = var.vpc_name }, var.tags)
}

resource "aws_subnet" "main" {
  for_each          = local.subnt_map
  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value.cidr_block
  availability_zone = join("", [var.region, each.value.az])
  tags              = merge({ "Name" = each.key }, var.tags)
}

