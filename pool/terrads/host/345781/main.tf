provider "aws" {
  region = "us-east-2"
}

resource "aws_vpc" "ashvpc" {
  cidr_block       = "10.0.0.0/16"
  instance_tenancy = "default"

  tags = {
    Name = "testvpc1"
  }
}

resource "aws_subnet" "public-a" {
  vpc_id     = aws_vpc.ashvpc.id
  cidr_block = "10.0.2.0/28"

  tags = {
    Name = "public-a"
  }
}

resource "aws_subnet" "private-a" {
  vpc_id     = aws_vpc.ashvpc.id
  cidr_block = "10.0.1.0/28"

  tags = {
    Name = "private-a"
  }
}

output "value1" {
	value = "${aws_vpc.ashvpc.id}"
}

output "value2" {
	value = "${aws_subnet.public-a.id}"
}

output "value3" {
	value = "${aws_subnet.private-a.id}"
}