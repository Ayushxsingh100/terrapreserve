resource "aws_vpc" "main" {
  cidr_block = var.vpc_cidr_block
  tags       = var.vpc_tags
}

resource "aws_subnet" "subnet" {
  for_each                = var.subnets
  availability_zone       = each.value.az
  vpc_id                  = aws_vpc.main.id
  tags                    = each.value.tags
  map_public_ip_on_launch = each.value.public
  cidr_block              = each.value.cidr
}
