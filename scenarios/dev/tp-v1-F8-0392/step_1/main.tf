### Route Tables ###

resource "aws_route_table" "private1" {
  vpc_id = var.vpc_id
  tags = {
    Name = "rt-${var.workload}-priv1"
  }
}

resource "aws_route_table" "private2" {
  vpc_id = var.vpc_id
  tags = {
    Name = "rt-${var.workload}-priv2"
  }
}

resource "aws_route_table" "private3" {
  vpc_id = var.vpc_id
  tags = {
    Name = "rt-${var.workload}-priv3"
  }
}

### Subnets ###

resource "aws_subnet" "private1" {
  vpc_id            = var.vpc_id
  cidr_block        = "10.0.91.0/24"
  availability_zone = var.az1

  tags = {
    Name = "subnet-${var.workload}-priv1"
  }
}

resource "aws_subnet" "private2" {
  vpc_id            = var.vpc_id
  cidr_block        = "10.0.92.0/24"
  availability_zone = var.az2

  tags = {
    Name = "subnet-${var.workload}-priv2"
  }
}

resource "aws_subnet" "private3" {
  vpc_id            = var.vpc_id
  cidr_block        = "10.0.93.0/24"
  availability_zone = var.az3

  tags = {
    Name = "subnet-${var.workload}-priv3"
  }
}

### Routes ###

resource "aws_route_table_association" "private1" {
  subnet_id      = aws_subnet.private1.id
  route_table_id = aws_route_table.private1.id
}

resource "aws_route_table_association" "private2" {
  subnet_id      = aws_subnet.private2.id
  route_table_id = aws_route_table.private2.id
}

resource "aws_route_table_association" "private3" {
  subnet_id      = aws_subnet.private3.id
  route_table_id = aws_route_table.private3.id
}
