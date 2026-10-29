resource "aws_subnet" "subnet" {
  vpc_id     = aws_vpc.vpc_cidr.id
  for_each   = var.network.subnets
  cidr_block = each.key
}