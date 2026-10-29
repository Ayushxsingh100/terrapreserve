terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.27"
    }
  }

  required_version = ">= 0.14.9"
}

provider "aws" {
  
  region        = "eu-central-1"
}

resource "aws_vpc" "example_app" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name        = "example_app_server_vpc"
  }
}

resource "aws_subnet" "example_app_subnet_a" {
  vpc_id            = aws_vpc.example_app.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "eu-central-1a"

  tags = {
    Name        = "example_app_subnet_a"
  }
}

resource "aws_instance" "app_server" {
  ami           = "ami-06ec8443c2a35b0ba"
  instance_type = "t2.micro"
  subnet_id     = aws_subnet.example_app_subnet_a.id

  tags = {
    Name        = "example_app_server_instance"
  }
}