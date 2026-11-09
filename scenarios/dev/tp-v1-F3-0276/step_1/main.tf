resource "aws_subnet" "public" {
  count                   = var.public_subnet_count
  vpc_id                  = var.vpc_id
  cidr_block              = element(var.public_cidr_blocks, count.index)
  availability_zone       = element(var.public_availability_zones, count.index)
  map_public_ip_on_launch = true

  tags = {
    Name                                        = "${var.public_subnet_name}-${count.index + 1}"
    Env                                         = var.env
    "kubernetes.io/cluster/${var.cluster_name}" = "owned"
    "kubernetes.io/role/elb"                    = "1"
    Terraform                                   = "true"
  }

}

resource "aws_subnet" "private" {
  count                   = var.private_subnet_count
  vpc_id                  = var.vpc_id
  cidr_block              = element(var.private_cidr_blocks, count.index)
  availability_zone       = element(var.private_availability_zones, count.index)
  map_public_ip_on_launch = false

  tags = {
    Name                                        = "${var.private_subnet_name}-${count.index + 1}"
    Env                                         = var.env
    "kubernetes.io/cluster/${var.cluster_name}" = "owned"
    "kubernetes.io/role/internal-elb"           = "1"
    Terraform                                   = "true"
  }

}
