resource "aws_vpc" "prod_vpc" {
  cidr_block           = "10.72.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "prod_igw" {
  vpc_id = aws_vpc.prod_vpc.id
}

resource "aws_subnet" "prod_app_subnet" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.72.1.0/24"
  vpc_id            = aws_vpc.prod_vpc.id
}

resource "aws_subnet" "prod_app_subnet_b" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.72.2.0/24"
  vpc_id            = aws_vpc.prod_vpc.id
}

resource "aws_subnet" "prod_db_subnet_1" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.72.10.0/24"
  vpc_id            = aws_vpc.prod_vpc.id
}

resource "aws_subnet" "prod_db_subnet_2" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.72.11.0/24"
  vpc_id            = aws_vpc.prod_vpc.id
}

resource "aws_route_table" "prod_public_rt" {
  vpc_id = aws_vpc.prod_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.prod_igw.id
  }
}

resource "aws_route_table_association" "prod_rta_app" {
  route_table_id = aws_route_table.prod_public_rt.id
  subnet_id      = aws_subnet.prod_app_subnet.id
}

resource "aws_route_table_association" "prod_rta_app_b" {
  route_table_id = aws_route_table.prod_public_rt.id
  subnet_id      = aws_subnet.prod_app_subnet_b.id
}

resource "aws_route_table" "prod_db_rt" {
  vpc_id = aws_vpc.prod_vpc.id
}

resource "aws_route_table_association" "prod_rta_db_1" {
  route_table_id = aws_route_table.prod_db_rt.id
  subnet_id      = aws_subnet.prod_db_subnet_1.id
}

resource "aws_route_table_association" "prod_rta_db_2" {
  route_table_id = aws_route_table.prod_db_rt.id
  subnet_id      = aws_subnet.prod_db_subnet_2.id
}
