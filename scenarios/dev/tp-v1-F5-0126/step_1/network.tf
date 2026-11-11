resource "aws_vpc" "platform" {
  cidr_block           = "10.190.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "edge" {
  vpc_id = aws_vpc.platform.id
}

resource "aws_subnet" "service" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.190.1.0/24"
  vpc_id            = aws_vpc.platform.id
}

resource "aws_subnet" "storage_1" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.190.10.0/24"
  vpc_id            = aws_vpc.platform.id
}

resource "aws_subnet" "storage_2" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.190.11.0/24"
  vpc_id            = aws_vpc.platform.id
}

resource "aws_subnet" "storage_3" {
  availability_zone = "us-east-1c"
  cidr_block        = "10.190.12.0/24"
  vpc_id            = aws_vpc.platform.id
}

resource "aws_route_table" "edge_routes" {
  vpc_id = aws_vpc.platform.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.edge.id
  }
}

resource "aws_route_table_association" "route_link_app" {
  route_table_id = aws_route_table.edge_routes.id
  subnet_id      = aws_subnet.service.id
}

resource "aws_route_table" "storage_routes" {
  vpc_id = aws_vpc.platform.id
}

resource "aws_route_table_association" "route_link_db_1" {
  route_table_id = aws_route_table.storage_routes.id
  subnet_id      = aws_subnet.storage_1.id
}

resource "aws_route_table_association" "route_link_db_2" {
  route_table_id = aws_route_table.storage_routes.id
  subnet_id      = aws_subnet.storage_2.id
}

resource "aws_route_table_association" "route_link_db_3" {
  route_table_id = aws_route_table.storage_routes.id
  subnet_id      = aws_subnet.storage_3.id
}
