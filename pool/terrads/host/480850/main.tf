terraform {
  required_version = ">= 1.5.0"
}

locals {
  azs  = [for i, cidr in var.private_subnet_cidr_blocks : "${var.region}${var.region-letters[i]}"]
  tags = merge(var.default_tags, var.tags)
}

resource "aws_vpc" "vpc" {
  cidr_block = var.cidr_blocks

  tags = merge(local.tags, { Name = "${var.env}-${var.name}" })
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.vpc.id
  tags   = merge(local.tags, { Name = "${var.env}-${var.name}-igw" })
}

resource "aws_subnet" "private_subnets" {
  count = length(var.private_subnet_cidr_blocks)

  vpc_id            = aws_vpc.vpc.id
  cidr_block        = var.private_subnet_cidr_blocks[count.index]
  availability_zone = local.azs[count.index]

  tags = merge(local.tags, { Name = "${var.env}-${var.name}-subnet" })
}
