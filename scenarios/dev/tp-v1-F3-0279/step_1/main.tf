
resource "aws_vpc" "main" {
  cidr_block = var.vpc_config.cidr_block
  tags = {
    Name = var.vpc_config.name
  }
}

resource "aws_subnet" "main" {
  vpc_id = aws_vpc.main.id
  for_each = var.subnet_config
    cidr_block = each.value.cidr_block #key={cidr,az}
    availability_zone = each.value.az
    tags = {
      Name =each.key
      }
}


locals {
    #if public == true then add to public_subnets
    public_subnets = {for key, subnet in var.subnet_config : key => subnet if subnet.public}
    private_subnets = {for key, subnet in var.subnet_config : key => subnet if !subnet.public}
}

#if there is atleast 1 public subnet
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  count = length(local.public_subnets) > 0 ? 1 : 0
}

resource "aws_route_table" "main" {
  vpc_id = aws_vpc.main.id
  count = length(local.public_subnets) > 0 ? 1 : 0
  route  {
    cidr_block="0.0.0.0/0"
    gateway_id = aws_internet_gateway.main[0].id
  }
}

resource "aws_route_table_association" "main" {
  for_each = local.public_subnets
  subnet_id = aws_subnet.main[each.key].id
  route_table_id = aws_route_table.main[0].id
}