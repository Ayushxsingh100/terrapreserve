resource "aws_vpc" "net" {
  cidr_block           = "10.79.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.net.id
}

resource "aws_subnet" "pub" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.79.1.0/24"
  vpc_id            = aws_vpc.net.id
}

resource "aws_subnet" "priv_1" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.79.10.0/24"
  vpc_id            = aws_vpc.net.id
}

resource "aws_subnet" "priv_2" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.79.11.0/24"
  vpc_id            = aws_vpc.net.id
}

resource "aws_subnet" "priv_3" {
  availability_zone = "us-east-1c"
  cidr_block        = "10.79.12.0/24"
  vpc_id            = aws_vpc.net.id
}

resource "aws_route_table" "pub" {
  vpc_id = aws_vpc.net.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }
}

resource "aws_route_table_association" "ra_app" {
  route_table_id = aws_route_table.pub.id
  subnet_id      = aws_subnet.pub.id
}

resource "aws_route_table" "priv" {
  vpc_id = aws_vpc.net.id
}

resource "aws_route_table_association" "ra_db_1" {
  route_table_id = aws_route_table.priv.id
  subnet_id      = aws_subnet.priv_1.id
}

resource "aws_route_table_association" "ra_db_2" {
  route_table_id = aws_route_table.priv.id
  subnet_id      = aws_subnet.priv_2.id
}

resource "aws_route_table_association" "ra_db_3" {
  route_table_id = aws_route_table.priv.id
  subnet_id      = aws_subnet.priv_3.id
}
