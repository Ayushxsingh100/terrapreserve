terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }

  required_version = ">= 1.8.0"
}

# Configure the AWS Provider
provider "aws" {
  region = var.region
}

# Create VPC
resource "aws_vpc" "wp-vpc" {
  cidr_block       = "10.0.0.0/16"
  instance_tenancy = "default"

  tags = {
    Name = "wp-tf"
  }
}

# Create Internet Gateway
resource "aws_internet_gateway" "wp-internet-gw" {
  vpc_id = aws_vpc.wp-vpc.id

  tags = {
    Name = "wp-internet-gw"
  }
}

# Create Route Table
resource "aws_route_table" "wp-route-table" {
  vpc_id = aws_vpc.wp-vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.wp-internet-gw.id
  }

  tags = {
    Name = "wp-route-table"
  }
}

# Create Subnet
resource "aws_subnet" "wp-subnet" {
  vpc_id            = aws_vpc.wp-vpc.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.region}a"

  tags = {
    Name = "wp-subnet"
  }
}

# Associate Route Table with Subnet
resource "aws_route_table_association" "wp-route-table-association" {
  subnet_id      = aws_subnet.wp-subnet.id
  route_table_id = aws_route_table.wp-route-table.id
}

# Create Security Group
resource "aws_security_group" "wp-allow-ssh" {
  name        = var.name_security_group
  description = "Allow SSH and HTTP inbound and outbound traffic"
  vpc_id      = aws_vpc.wp-vpc.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "wp-allow-ssh"
  }
}

# Create EC2 Instance
resource "aws_instance" "wp-server" {
  ami                    = var.ami_aws_instance
  instance_type          = var.type_aws_instance
  vpc_security_group_ids = [aws_security_group.wp-allow-ssh.id]
  key_name               = var.key_aws_instance

  monitoring                  = true
  subnet_id                   = aws_subnet.wp-subnet.id
  associate_public_ip_address = true

  tags = {
    Name = "wp-server"
  }
}
