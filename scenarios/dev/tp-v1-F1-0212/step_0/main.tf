resource "aws_subnet" "subnet" {
  vpc_id                  = var.vpc_id
  availability_zone       = var.availability_zone
  cidr_block              = var.cidr_block
  map_public_ip_on_launch = false

  tags = merge(
    var.tags,
    {
      Name = "${var.prefix}-subnet-private-${var.availability_zone}"
    }
  )
}

resource "aws_route_table" "rt" {
  vpc_id = var.vpc_id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = var.nat_gw_id
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.prefix}-private-rtb-${var.availability_zone}"
    }
  )
}

resource "aws_route_table_association" "rt_a" {
  route_table_id = aws_route_table.rt.id
  subnet_id      = aws_subnet.subnet.id
}
