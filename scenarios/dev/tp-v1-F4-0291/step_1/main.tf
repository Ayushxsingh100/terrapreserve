
resource "aws_subnet" "public" {
  count                   = length(var.azs)
  vpc_id                  = var.vpc_id
  cidr_block              = var.public_cidrs[count.index]
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = true
  tags = { Name = "${var.vpc_id}-public-${count.index}" }
}

resource "aws_subnet" "private" {
  count                   = length(var.azs)
  vpc_id                  = var.vpc_id
  cidr_block              = var.private_cidrs[count.index]
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = false
  tags = { Name = "${var.vpc_id}-private-${count.index}" }
}