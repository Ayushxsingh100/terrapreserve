resource "aws_vpc" "prod_vpc" {
  cidr_block           = "10.110.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "prod_igw" {
  vpc_id = aws_vpc.prod_vpc.id
}

resource "aws_subnet" "prod_app_subnet" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.110.1.0/24"
  vpc_id            = aws_vpc.prod_vpc.id
}

resource "aws_subnet" "prod_db_subnet" {
  count = 2

  availability_zone = ["us-east-1a", "us-east-1b"][count.index]
  cidr_block        = ["10.110.10.0/24", "10.110.11.0/24"][count.index]
  vpc_id            = aws_vpc.prod_vpc.id
}

resource "aws_subnet" "prod_app_subnet_spare" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.110.200.0/24"
  vpc_id            = aws_vpc.prod_vpc.id
}

resource "aws_route_table" "prod_public_rt_a" {
  vpc_id = aws_vpc.prod_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.prod_igw.id
  }
}

resource "aws_route_table_association" "prod_rta_app" {
  route_table_id = aws_route_table.prod_public_rt_a.id
  subnet_id      = aws_subnet.prod_app_subnet.id
}

resource "aws_route_table" "prod_db_rt" {
  count = 2

  vpc_id = aws_vpc.prod_vpc.id
}

resource "aws_route_table_association" "prod_rta_db" {
  count = 2

  route_table_id = aws_route_table.prod_db_rt[count.index].id
  subnet_id      = aws_subnet.prod_db_subnet[count.index].id
}
