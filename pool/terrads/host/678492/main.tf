terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "eu-west-3"
}

resource "aws_vpc" "soc_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "soc-vpc"
  }
}

resource "aws_subnet" "soc_subnet" {
  vpc_id                  = aws_vpc.soc_vpc.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "eu-west-3a"

  tags = {
    Name = "soc-subnet"
  }
}

resource "aws_internet_gateway" "soc_igw" {
  vpc_id = aws_vpc.soc_vpc.id

  tags = {
    Name = "soc-igw"
  }
}

resource "aws_route_table" "soc_rt" {
  vpc_id = aws_vpc.soc_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.soc_igw.id
  }

  tags = {
    Name = "soc-route-table"
  }
}

resource "aws_route_table_association" "soc_rta" {
  subnet_id      = aws_subnet.soc_subnet.id
  route_table_id = aws_route_table.soc_rt.id
}
