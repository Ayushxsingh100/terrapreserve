locals {
  public_subnets = {
    for key, config in var.subnet_config : key => config if config.public
  }
  
  private_subnets = {
    for key, config in var.subnet_config : key => config if !config.public
  }

}


data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "vpc" {
  cidr_block = var.vpc_config.cidr_block
  tags = {
    Name = var.vpc_config.name
  }
}


resource "aws_subnet" "name" {
  for_each          = var.subnet_config # for_each used to interrate map, it returns each.key and each.value
  vpc_id            = aws_vpc.vpc.id
  cidr_block        = each.value.cidr_block
  availability_zone = each.value.az

  tags = {
    Name = each.key
    Access = each.value.public ? "Public" : "Private"
  }

  # use join to convert list to string
  lifecycle {
    precondition {
      condition     = contains(data.aws_availability_zones.available.names, each.value.az)
      error_message = <<-EOT
      The AZ "${each.value.az}" provided for subnet "${each.key}" is invalid.
      The applied AWS region "${data.aws_availability_zones.available.id}" supports the following Azs:
      ${join(",", data.aws_availability_zones.available.names)}                  
      EOT
    }
  }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.vpc.id
  count  = length(local.public_subnets) > 0 ? 1 : 0 # if public_subnets > 0 then create 1 IGW else 0 IGW
}

resource "aws_route_table" "public_rtb" {
  vpc_id = aws_vpc.vpc.id
  count  = length(local.public_subnets) > 0 ? 1 : 0

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this[0].id # when we use count, resource become list, so we need to use index [0]
  }
}

resource "aws_route_table_association" "public" {
  for_each       = local.public_subnets
  subnet_id      = aws_subnet.name[each.key].id
  route_table_id = aws_route_table.public_rtb[0].id
}