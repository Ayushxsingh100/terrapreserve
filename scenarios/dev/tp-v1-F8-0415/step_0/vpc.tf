resource "aws_vpc" "this" {
  cidr_block = var.vpc_cidr_block

  tags = {
    Name        = var.vpcname
    Provisioner = "terraform"
  }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = {
    Name        = var.igwname
    Provisioner = "terraform"
  }
}

resource "aws_subnet" "public_subnet" {
  count             = length(var.public_subnet_cidrs)
  vpc_id            = aws_vpc.this.id
  cidr_block        = element(var.public_subnet_cidrs, count.index)
  availability_zone = element(var.azs, count.index)

  tags = {
    Name        = "Public Subnet ${count.index + 1}"
    Provisioner = "terraform"
  }
}

resource "aws_subnet" "private_subnet" {
  count             = length(var.private_subnet_cidrs)
  vpc_id            = aws_vpc.this.id
  cidr_block        = element(var.private_subnet_cidrs, count.index)
  availability_zone = element(var.azs, count.index)

  tags = {
    Name        = "Private Subnet ${count.index + 1}"
    Provisioner = "terraform"
  }
}

resource "aws_route_table" "this" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = {
    Name        = "Route table VPC IGW"
    Provisioner = "terraform"
  }
}

resource "aws_route_table_association" "this" {

  count = length(var.public_subnet_cidrs)

  subnet_id = element(aws_subnet.public_subnet[*].id, count.index)

  route_table_id = aws_route_table.this.id

}