resource "aws_vpc" "terra" {
  cidr_block       = "10.0.0.0/18"
  enable_dns_support = true
  instance_tenancy = "default"
  

  tags = {
    Name = "terra"
  }
}

resource "aws_subnet" "terra_pub" {
  vpc_id     = aws_vpc.terra.id
  cidr_block = "10.0.0.0/20"
  map_public_ip_on_launch = true

  tags = {
    Name = "terra_pub"
  }
}

resource "aws_subnet" "terra_pub2" {
  vpc_id     = aws_vpc.terra.id
  cidr_block = "10.0.16.0/20"
  map_public_ip_on_launch = true

  tags = {
    Name = "terra_pub2"
  }
}

resource "aws_subnet" "terra_private" {
  vpc_id     = aws_vpc.terra.id
  cidr_block = "10.0.32.0/20"

  tags = {
    Name = "terra_private"
  }
}

resource "aws_internet_gateway" "terra_gw" {
  vpc_id = aws_vpc.terra.id

  tags = {
    Name = "terra_gw"
  }
}

resource "aws_route_table" "terra_rtb" {
  vpc_id = aws_vpc.terra.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.terra_gw.id
  }

  tags = {
    Name = "terra_rtb"
  }
}