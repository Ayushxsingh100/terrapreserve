############################################
## Network Two AZ Public & Private - Main ##
############################################

# Create the VPC
resource "aws_vpc" "vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  tags = {
    Name = "${lower(var.vpc_name)}"

  }
}

# Declare the data source
data "aws_availability_zones" "available" {
  state = "available"
}

# Define the public subnet 1
resource "aws_subnet" "public-subnet1" {
  vpc_id            = aws_vpc.vpc.id
  cidr_block        = var.public_subnet_cidr1
  availability_zone = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true
  tags = {
    Name = "${lower(var.vpc_name)}-public-subnet1"

  }
}

# Define the public subnet 2
resource "aws_subnet" "public-subnet2" {
  vpc_id            = aws_vpc.vpc.id
  cidr_block        = var.public_subnet_cidr2
  availability_zone = data.aws_availability_zones.available.names[1]
  map_public_ip_on_launch = true
  tags = {
    Name = "${lower(var.vpc_name)}-public-subnet2"

  }
}

# Define the internet gateway
resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.vpc.id
  tags = {
    Name = "${lower(var.vpc_name)}-gw"

  }
}

# Define the public route table
resource "aws_route_table" "public-rt" {
  vpc_id = aws_vpc.vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }
  tags = {
    Name = "${lower(var.vpc_name)}-public-subnet-rt"

  }
}

# Assign the public route table to the public subnet1
resource "aws_route_table_association" "public-rt-association1" {
  subnet_id      = aws_subnet.public-subnet1.id
  route_table_id = aws_route_table.public-rt.id
}

# Assign the public route table to the public subnet2
resource "aws_route_table_association" "public-rt-association2" {
  subnet_id      = aws_subnet.public-subnet2.id
  route_table_id = aws_route_table.public-rt.id
}


# Define the private subnet 1
resource "aws_subnet" "private-subnet1" {
  vpc_id            = aws_vpc.vpc.id
  cidr_block        = var.private_subnet_cidr1
  availability_zone = data.aws_availability_zones.available.names[0]
  tags = {
    Name = "${lower(var.vpc_name)}-private-subnet1"

  }
}

# Define the private subnet 2
resource "aws_subnet" "private-subnet2" {
  vpc_id            = aws_vpc.vpc.id
  cidr_block        = var.private_subnet_cidr2
  availability_zone = data.aws_availability_zones.available.names[1]
  tags = {
    Name = "${lower(var.vpc_name)}-private-subnet2"

  }
}

# Define the private route table
resource "aws_route_table" "private-rt1" {
  vpc_id = aws_vpc.vpc.id
  tags = {
    Name = "${lower(var.vpc_name)}-private-subnet-rt1"

  }
}

# Define the private route table
resource "aws_route_table" "private-rt2" {
  vpc_id = aws_vpc.vpc.id
  tags = {
    Name = "${lower(var.vpc_name)}-private-subnet-rt2"

  }
}

# Assign the private route table to the private subnet1
resource "aws_route_table_association" "private-rt-association1" {
  subnet_id      = aws_subnet.private-subnet1.id
  route_table_id = aws_route_table.private-rt1.id
}

# Assign the private route table to the private subnet2
resource "aws_route_table_association" "private-rt-association2" {
  subnet_id      = aws_subnet.private-subnet2.id
  route_table_id = aws_route_table.private-rt2.id
}
