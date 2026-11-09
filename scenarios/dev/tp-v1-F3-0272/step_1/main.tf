

resource "aws_subnet" "test-subnet" {
  vpc_id     = var.target_vpc
  cidr_block = var.subnet_cidr

  tags = {
    Name = var.cluster_name
  }
}