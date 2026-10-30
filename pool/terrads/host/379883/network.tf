resource "aws_vpc" "vpc" {
  cidr_block = "172.16.0.0/16"
  tags       = var.tags
}

resource "aws_subnet" "subnet" {
  vpc_id                  = aws_vpc.vpc.id
  cidr_block              = "172.16.10.0/24"
  map_public_ip_on_launch = true
  availability_zone       = var.az
  tags                    = var.tags
}

resource "aws_internet_gateway" "gateway" {
  vpc_id = aws_vpc.vpc.id
  tags   = var.tags
}

resource "aws_route_table" "route-table" {
  vpc_id = aws_vpc.vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gateway.id
  }
  tags = var.tags
}

resource "aws_route_table_association" "route-table-association" {
  subnet_id      = aws_subnet.subnet.id
  route_table_id = aws_route_table.route-table.id
}
