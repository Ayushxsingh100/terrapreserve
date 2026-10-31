# This is where you put your resource declaration

data "aws_availability_zones" "default" {}

resource "aws_vpc" "vpc" {
  cidr_block = var.vpc_cidr
  tags       = merge(local.common_tags, { Name = "vpc-${local.common_tags.environment}" })
}

resource "aws_internet_gateway" "default" {
  vpc_id = aws_vpc.vpc.id
  tags   = merge(local.common_tags, { Name = "igw-${local.common_tags.environment}" })
}

resource "aws_subnet" "public-sub1" {
  cidr_block        = cidrsubnet(aws_vpc.vpc.cidr_block, 8, 1)
  availability_zone = data.aws_availability_zones.default.names[0]
  vpc_id            = aws_vpc.vpc.id
  tags              = merge(local.common_tags, { Name = "public-subnet1-${local.common_tags.environment}" })
}

resource "aws_subnet" "public-sub2" {
  cidr_block        = cidrsubnet(aws_vpc.vpc.cidr_block, 8, 2)
  availability_zone = data.aws_availability_zones.default.names[1]
  vpc_id            = aws_vpc.vpc.id
  tags              = merge(local.common_tags, { Name = "public-subnet2-${local.common_tags.environment}" })
}

resource "aws_subnet" "private-sub1" {
  cidr_block        = cidrsubnet(aws_vpc.vpc.cidr_block, 8, 3)
  availability_zone = data.aws_availability_zones.default.names[0]
  vpc_id            = aws_vpc.vpc.id
  tags              = merge(local.common_tags, { Name = "private-subnet1-${local.common_tags.environment}" })
}

resource "aws_subnet" "private-sub2" {
  cidr_block        = cidrsubnet(aws_vpc.vpc.cidr_block, 8, 4)
  availability_zone = data.aws_availability_zones.default.names[1]
  vpc_id            = aws_vpc.vpc.id
  tags              = merge(local.common_tags, { Name = "private-subnet2-${local.common_tags.environment}" })
}

resource "aws_route_table" "public_rtb" {
  vpc_id = aws_vpc.vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.default.id
  }
  tags = merge(local.common_tags, { Name = "public-rtb-${local.common_tags.environment}" })
}

resource "aws_route_table_association" "association1" {
  route_table_id = aws_route_table.public_rtb.id
  subnet_id      = aws_subnet.public-sub1.id
}

resource "aws_route_table_association" "association2" {
  route_table_id = aws_route_table.public_rtb.id
  subnet_id      = aws_subnet.public-sub2.id
}
