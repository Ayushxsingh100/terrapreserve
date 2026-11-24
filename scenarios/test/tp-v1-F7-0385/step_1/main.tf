resource "aws_vpc" "main" {
  cidr_block = var.vpc_config.cidr_block
  tags       = {
    Name     = var.vpc_config.name
  }
}

resource "aws_subnet" "main" {
  for_each = var.subnet_config
  vpc_id   = aws_vpc.main.id

  cidr_block        = each.value.cidr_block
  availability_zone = each.value.availability_zone

  tags = {
    Name = each.key
  }
    
}

locals {
  public_subnet = {
    #key = {} public is true in subnet_config
    for key, config in var.subnet_config : key => config if config.public
  }
  private_subnet = {
    #key = {} public is false in subnet_config
    for key, config in var.subnet_config : key => config if !config.public
  }
}
#Internet Gateway, if there is atleast one public subnet
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  count  =  length(keys(local.public_subnet)) > 0 ? 1 : 0
}

#Routing Table
resource "aws_route_table" "main" {
  vpc_id = aws_vpc.main.id
  count  = length(keys(local.public_subnet)) > 0 ? 1 : 0

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main[0].id
  }
}
#Route Table Association
resource "aws_route_table_association" "main" {
  for_each       = local.public_subnet
  subnet_id      = aws_subnet.main[each.key].id
  route_table_id = aws_route_table.main[0].id
}