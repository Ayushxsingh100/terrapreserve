resource "aws_vpc" "main" {
  cidr_block           = "10.124.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "app" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.124.1.0/24"
  vpc_id            = aws_vpc.main.id
}

resource "aws_subnet" "db_1" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.124.10.0/24"
  vpc_id            = aws_vpc.main.id
}

resource "aws_subnet" "db_2" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.124.11.0/24"
  vpc_id            = aws_vpc.main.id
}

resource "aws_subnet" "db_3" {
  availability_zone = "us-east-1c"
  cidr_block        = "10.124.12.0/24"
  vpc_id            = aws_vpc.main.id
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}

resource "aws_route_table_association" "rta_app" {
  route_table_id = aws_route_table.public.id
  subnet_id      = aws_subnet.app.id
}
