data "aws_availability_zones" "az" {
  state = "available"
}

resource "aws_vpc" "custom" {
  cidr_block           = var.cidr_block
  enable_dns_support   = true
  enable_dns_hostnames = true

  # Enable IPv6 support
  assign_generated_ipv6_cidr_block = true

  tags = {
    Name = "j-${var.project_name}-vpc"
  }
}

resource "aws_subnet" "public" {
  count             = length(var.public_cidr_block)
  vpc_id            = aws_vpc.custom.id
  cidr_block        = var.public_cidr_block[count.index]
  availability_zone = data.aws_availability_zones.az.names[count.index]

  # Associate IPv6 CIDR
  ipv6_cidr_block = cidrsubnet(aws_vpc.custom.ipv6_cidr_block, 8, count.index + length(data.aws_availability_zones.az.names))

  tags = {
    Name = "j-${var.project_name}-public-subnet-${count.index + 1}"
  }
}

resource "aws_subnet" "private" {
  count             = length(var.private_cidr_block)
  vpc_id            = aws_vpc.custom.id
  cidr_block        = var.private_cidr_block[count.index]
  availability_zone = data.aws_availability_zones.az.names[count.index]

  # Optional IPv6 support
  ipv6_cidr_block = cidrsubnet(aws_vpc.custom.ipv6_cidr_block, 8, count.index)

  tags = {
    Name = "j-${var.project_name}-private-subnet-${count.index + 1}"
  }
}
