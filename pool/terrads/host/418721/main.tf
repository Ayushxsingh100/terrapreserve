terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.27"
    }
  }

  required_version = ">= 1.1.0"
}

provider "aws" {
  profile = "default"
  region  = "us-east-1"

  default_tags {
    tags = {
      Source = "Terraform"
    }
  }
}

resource "aws_vpc" "secure_cloud" {
  cidr_block           = "11.0.0.0/16"
  enable_dns_hostnames = true

  tags = {
    "Name" = "Secure cloud"
  }
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.secure_cloud.id

  tags = {
    "Name" = "DMZ gateway"
  }
}

resource "aws_route_table" "routing_table" {
  vpc_id = aws_vpc.secure_cloud.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.secure_cloud.id
  cidr_block              = "11.0.0.0/24"
  map_public_ip_on_launch = true

  tags = {
    "Name" = "DMZ"
  }
}

resource "aws_route_table_association" "internet_access" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.routing_table.id
}

resource "aws_security_group" "bitwarden_sg" {
  vpc_id = aws_vpc.secure_cloud.id
  ingress {
    description      = "TLS from everywhere"
    from_port        = 443
    to_port          = 443
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
  ingress {
    description      = "SSH from everywhere"
    from_port        = 22
    to_port          = 22
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
}

resource "aws_instance" "app_server" {
  ami                    = "ami-0f9fc25dd2506cf6d"
  instance_type          = "t2.micro"
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.bitwarden_sg.id]
  depends_on = [
    aws_internet_gateway.gw
  ]

  tags = {
    Name = "BitWarden"
  }
}
