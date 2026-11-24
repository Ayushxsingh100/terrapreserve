resource "aws_vpc" "main" {
  cidr_block           = "10.14.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "app" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.14.1.0/24"
  vpc_id            = aws_vpc.main.id
}

resource "aws_subnet" "db_1" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.14.10.0/24"
  vpc_id            = aws_vpc.main.id
}

resource "aws_subnet" "db_2" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.14.11.0/24"
  vpc_id            = aws_vpc.main.id
}

resource "aws_subnet" "db_3" {
  availability_zone = "us-east-1c"
  cidr_block        = "10.14.12.0/24"
  vpc_id            = aws_vpc.main.id
}

resource "aws_route_table" "public_a" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}

resource "aws_route_table_association" "rta_app" {
  route_table_id = aws_route_table.public_a.id
  subnet_id      = aws_subnet.app.id
}

resource "aws_route_table" "db_1" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table_association" "rta_db_1" {
  route_table_id = aws_route_table.db_1.id
  subnet_id      = aws_subnet.db_1.id
}

resource "aws_route_table" "db_2" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table_association" "rta_db_2" {
  route_table_id = aws_route_table.db_2.id
  subnet_id      = aws_subnet.db_2.id
}

resource "aws_route_table" "db_3" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table_association" "rta_db_3" {
  route_table_id = aws_route_table.db_3.id
  subnet_id      = aws_subnet.db_3.id
}
