


resource "aws_vpc" "this" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name    = "cloud-admin-foundations-vpc"
    Project = "aws-cloud-admin-foundations"
    Env     = "lab"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.this.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = var.tp_ds_aws_availability_zones_available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name    = "public-subnet"
    Project = "aws-cloud-admin-foundations"
    Env     = "lab"
  }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = {
    Name    = "vpc-igw"
    Project = "aws-cloud-admin-foundations"
    Env     = "lab"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = {
    Name    = "public-rt"
    Project = "aws-cloud-admin-foundations"
    Env     = "lab"
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.this.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = var.tp_ds_aws_availability_zones_available.names[0]

  tags = {
    Name    = "private-subnet"
    Project = "aws-cloud-admin-foundations"
    Env     = "lab"
  }
}
