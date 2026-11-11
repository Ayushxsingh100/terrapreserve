resource "aws_vpc" "vpc_main" {
  cidr_block           = "10.52.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "igw_main" {
  vpc_id = aws_vpc.vpc_main.id
}

resource "aws_subnet" "sub_app" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.52.1.0/24"
  vpc_id            = aws_vpc.vpc_main.id
}

resource "aws_subnet" "sub_db" {
  count = 3

  availability_zone = ["us-east-1a", "us-east-1b", "us-east-1c"][count.index]
  cidr_block        = ["10.52.10.0/24", "10.52.11.0/24", "10.52.12.0/24"][count.index]
  vpc_id            = aws_vpc.vpc_main.id
}

resource "aws_subnet" "sub_app_spare" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.52.200.0/24"
  vpc_id            = aws_vpc.vpc_main.id
}

resource "aws_route_table" "rt_public" {
  vpc_id = aws_vpc.vpc_main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw_main.id
  }
}

resource "aws_route_table_association" "rta_app" {
  route_table_id = aws_route_table.rt_public.id
  subnet_id      = aws_subnet.sub_app.id
}
