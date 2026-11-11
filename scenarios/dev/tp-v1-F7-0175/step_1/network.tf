resource "aws_vpc" "acme_vpc" {
  cidr_block           = "10.156.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "acme_igw" {
  vpc_id = aws_vpc.acme_vpc.id
}

resource "aws_subnet" "acme_app_subnet" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.156.1.0/24"
  vpc_id            = aws_vpc.acme_vpc.id
}

resource "aws_subnet" "acme_db_subnet" {
  count = 2

  availability_zone = ["us-east-1a", "us-east-1b"][count.index]
  cidr_block        = ["10.156.10.0/24", "10.156.11.0/24"][count.index]
  vpc_id            = aws_vpc.acme_vpc.id
}

resource "aws_route_table" "acme_public_rt_a" {
  vpc_id = aws_vpc.acme_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.acme_igw.id
  }
}

resource "aws_route_table_association" "acme_rta_app" {
  route_table_id = aws_route_table.acme_public_rt_a.id
  subnet_id      = aws_subnet.acme_app_subnet.id
}

resource "aws_route_table" "acme_db_rt" {
  count = 2

  vpc_id = aws_vpc.acme_vpc.id
}

resource "aws_route_table_association" "acme_rta_db" {
  count = 2

  route_table_id = aws_route_table.acme_db_rt[count.index].id
  subnet_id      = aws_subnet.acme_db_subnet[count.index].id
}
