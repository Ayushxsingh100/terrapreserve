resource "aws_vpc" "vpc" {
  cidr_block = var.cidr_block
}

resource "aws_subnet" "subnet" {
  vpc_id = aws_vpc.vpc.id

  availability_zone = "us-east-1a"
  cidr_block        = cidrsubnet(aws_vpc.vpc.cidr_block, 4, 1)
}
