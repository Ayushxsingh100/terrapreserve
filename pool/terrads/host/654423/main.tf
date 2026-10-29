
resource "aws_vpc" "network" {
  cidr_block = var.network.cidr
  tags = {
    Name = var.network.name
  }
}
resource "aws_subnet" "subnets" {
  count             = length(var.subnet_info)
  vpc_id            = aws_vpc.network.id
  availability_zone = var.subnet_info[count.index].azs
  cidr_block        = var.subnet_info[count.index].cidr
  tags = {
    Name = var.subnet_info[count.index].name
  }
} 