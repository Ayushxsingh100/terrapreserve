resource "aws_vpc" "main_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "main_vpc"
  }
}

# Create a public subnet
resource "aws_subnet" "main_vpc_public_subnet" {
  vpc_id                  = aws_vpc.main_vpc.id
  cidr_block              = var.vpc_public_subnet_cidr_1
  availability_zone       = "us-west-1a"
  map_public_ip_on_launch = true

  tags = {
    Name = "main_vpc_public_subnet"
  }
}

resource "aws_subnet" "main_vpc_public_subnet2" {
  vpc_id                  = aws_vpc.main_vpc.id
  cidr_block              = var.vpc_public_subnet_cidr_2
  availability_zone       = "us-west-1c"
  map_public_ip_on_launch = true

  tags = {
    Name = "main_vpc_public_subnet2"
  }
}

# Create an internet gateway
resource "aws_internet_gateway" "main_vpc_igw" {
  vpc_id = aws_vpc.main_vpc.id

  tags = {
    Name = "main_vpc_igw"
  }
}

# Create a route table for the public subnet
resource "aws_route_table" "public_subnet_route" {
  vpc_id = aws_vpc.main_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main_vpc_igw.id
  }

  tags = {
    Name = "public_subnet_route"
  }
}

# Associate the public subnet with the route table
resource "aws_route_table_association" "public_subnet_association" {
  subnet_id      = aws_subnet.main_vpc_public_subnet.id
  route_table_id = aws_route_table.public_subnet_route.id
}
