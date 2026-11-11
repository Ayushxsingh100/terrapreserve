resource "aws_vpc" "net" {
  cidr_block           = "10.129.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.net.id
}

resource "aws_subnet" "pub" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.129.1.0/24"
  vpc_id            = aws_vpc.net.id
}

resource "aws_subnet" "priv" {
  count = 2

  availability_zone = ["us-east-1a", "us-east-1b"][count.index]
  cidr_block        = ["10.129.10.0/24", "10.129.11.0/24"][count.index]
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
