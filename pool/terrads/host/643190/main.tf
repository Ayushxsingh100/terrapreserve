# VPC module

resource "aws_vpc" "dev_cicd_vpc" {
  cidr_block           = var.dev_cicd_vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "dev_cicd_vpc"
  }
}


resource "aws_subnet" "dev_cicd_vpc_public_subnet" {
  vpc_id                  = aws_vpc.dev_cicd_vpc.id
  cidr_block              = var.dev_cicd_vpc_public_subnet_cidr
  map_public_ip_on_launch = true
  availability_zone       = "us-east-2a"

  tags = {
    Name = "dev_cicd_vpc_public_subnet_1"
  }
}

resource "aws_security_group" "dev_cicd_vpc_public_subnet_security_group" {
  name        = "dev_public_subnet_security_group"
  description = "SSH inbound traffic"
  vpc_id      = aws_vpc.dev_cicd_vpc.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_client_ip]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.ssh_client_ip]
  }
}