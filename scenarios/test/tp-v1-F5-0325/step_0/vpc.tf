resource "aws_vpc" "vpc_cidr" {
  cidr_block = var.network.cidr
}