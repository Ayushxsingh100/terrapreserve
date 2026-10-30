terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      version               = "~> 6.4.0"
    }
  }
}
provider "aws" {
  region = "us-west-2"
}

resource "aws_vpc" "vpc" {
  cidr_block = var.cidr_block
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-${var.environment}-vpc"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.vpc.id

  tags = {
    Name = "${var.project_name}-${var.environment}-igw"
  }
}

resource "aws_subnet" "subnet_a" {
    vpc_id            = aws_vpc.vpc.id
    cidr_block        = var.subnet_az_a
    availability_zone = "us-west-2a"
    
    tags = {
        Name = "${var.project_name}-${var.environment}-subnet-a"
    }
  
}

resource aws_subnet "subnet_b" {
    vpc_id            = aws_vpc.vpc.id
    cidr_block        = var.subnet_az_b
    availability_zone = "us-west-2b"
    
    tags = {
        Name = "${var.project_name}-${var.environment}-subnet-b"
    }
  
}

resource "aws_route_table" "route_table" {
  vpc_id = aws_vpc.vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-route-table"
  }
  
}

resource "aws_route_table_association" "subnet_a_association" {
  subnet_id      = aws_subnet.subnet_a.id
  route_table_id = aws_route_table.route_table.id
}

resource "aws_route_table_association" "subnet_b_association" {
  subnet_id      = aws_subnet.subnet_b.id
  route_table_id = aws_route_table.route_table.id
}