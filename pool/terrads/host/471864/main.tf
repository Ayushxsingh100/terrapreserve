resource "aws_vpc" "main" {
  cidr_block = var.vpc_cidr
}

resource "aws_security_group" "public" {
  count = var.enable_public_subnets ? 1 : 0

  vpc_id = aws_vpc.main.id
}

output "public_sg" {
  value = var.enable_public_subnets ? aws_security_group.public[0].id : ""
  description = "Public Subnet IDs"
}

resource "aws_security_group_rule" "public_egress" {
  count = var.enable_public_subnets ? 1 : 0

  type = "egress"
  cidr_blocks = ["0.0.0.0/0"]
  description = "Allow internet egress"
  from_port = 0
  to_port = 65535
  protocol = "all"
  security_group_id = aws_security_group.public[0].id
}

resource "aws_internet_gateway" "main" {
  count = var.enable_public_subnets ? 1 : 0

  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "public" {
  for_each = {
    for index, az_name in
    slice(data.aws_availability_zones.available.names, 0, var.number_of_availability_zones)
    : az_name => cidrsubnet(aws_vpc.main.cidr_block, local.subnet_newbits, index)
    if var.enable_public_subnets
  }

  vpc_id            = aws_vpc.main.id
  availability_zone = each.key
  cidr_block        = each.value

  map_public_ip_on_launch = true
}

output "public_subnet_ids" {
  value = values(aws_subnet.public)[*].id
  description = "Public Subnet IDs"
}

resource "aws_route_table" "public" {
  count = var.enable_public_subnets ? 1 : 0

  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main[0].id
  }

  route {
    cidr_block = aws_vpc.main.cidr_block
    gateway_id = "local"
  }
}

resource "aws_route_table_association" "public" {
  for_each = var.enable_public_subnets ? aws_subnet.public : {}

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public[0].id
}

resource "aws_subnet" "nat" {
  for_each = {
    for index, az_name in
    slice(data.aws_availability_zones.available.names, 0, var.number_of_availability_zones)
    : az_name => cidrsubnet(aws_vpc.main.cidr_block, local.subnet_newbits, index + var.number_of_availability_zones)
    if var.enable_nat_subnets
  }

  vpc_id            = aws_vpc.main.id
  availability_zone = each.key
  cidr_block        = each.value
}

resource "aws_subnet" "private" {
  for_each = {
    for index, az_name in
    slice(data.aws_availability_zones.available.names, 0, var.number_of_availability_zones)
    : az_name => cidrsubnet(aws_vpc.main.cidr_block, local.subnet_newbits, index + (2 * var.number_of_availability_zones))
    if var.enable_private_subnets
  }

  vpc_id            = aws_vpc.main.id
  availability_zone = each.key
  cidr_block        = each.value
}
