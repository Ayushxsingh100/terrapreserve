provider "aws" {
  region = "us-east-1"
  access_key = ""
  secret_key = ""
}

resource "aws_instance" "my-server" {
  ami           = "ami-080e1f13689e07408"
  instance_type = "t2.micro"

  tags = {
    Name = "my-tf-instance"
    Owner       = "David"
  }
}

resource "aws_vpc" "first-vpc" {
  cidr_block = "10.0.0.0/16"
  tags = {
    Name = "prod-vpc"
  }
}

resource "aws_vpc" "second-vpc" {
  cidr_block = "10.0.0.0/16"
  tags = {
    Name = "dev-vpc"
  }
}

resource "aws_subnet" "subnet-2" {
  vpc_id     = aws_vpc.second-vpc.id
  cidr_block = "10.0.1.0/24"

  tags = {
    Name = "dev-subnet"
  }
}
