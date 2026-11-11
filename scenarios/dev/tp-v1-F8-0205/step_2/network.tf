resource "aws_vpc" "network" {
  cidr_block           = "10.23.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "gateway" {
  vpc_id = aws_vpc.network.id
}

resource "aws_subnet" "web_tier" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.23.1.0/24"
  vpc_id            = aws_vpc.network.id
}

resource "aws_subnet" "data_tier_1" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.23.10.0/24"
  vpc_id            = aws_vpc.network.id
}

resource "aws_subnet" "data_tier_2" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.23.11.0/24"
  vpc_id            = aws_vpc.network.id
}

resource "aws_subnet" "data_tier_3" {
  availability_zone = "us-east-1c"
  cidr_block        = "10.23.12.0/24"
  vpc_id            = aws_vpc.network.id
}

resource "aws_route_table" "public_route_a" {
  vpc_id = aws_vpc.network.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gateway.id
  }
}

resource "aws_route_table_association" "assoc_app" {
  route_table_id = aws_route_table.public_route_a.id
  subnet_id      = aws_subnet.web_tier.id
}

resource "aws_route_table" "data_route_1" {
  vpc_id = aws_vpc.network.id
}

resource "aws_route_table_association" "assoc_db_1" {
  route_table_id = aws_route_table.data_route_1.id
  subnet_id      = aws_subnet.data_tier_1.id
}

resource "aws_route_table" "data_route_2" {
  vpc_id = aws_vpc.network.id
}

resource "aws_route_table_association" "assoc_db_2" {
  route_table_id = aws_route_table.data_route_2.id
  subnet_id      = aws_subnet.data_tier_2.id
}

resource "aws_route_table" "data_route_3" {
  vpc_id = aws_vpc.network.id
}

resource "aws_route_table_association" "assoc_db_3" {
  route_table_id = aws_route_table.data_route_3.id
  subnet_id      = aws_subnet.data_tier_3.id
}
