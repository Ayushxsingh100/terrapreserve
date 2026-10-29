variable "enviroment_name" {}
variable "vpc_range" {
    default = "10.0.1.0/26"
}
variable "subnet_range" {
    default = "10.0.1.0/28"
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_range

  tags = {
    Name = var.enviroment_name
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = var.enviroment_name
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
      cidr_block = "0.0.0.0/0"
      gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = var.enviroment_name
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_subnet" "public" {
  vpc_id     = aws_vpc.main.id
  cidr_block = var.subnet_range
  map_public_ip_on_launch = true
  availability_zone = "us-east-1a"

  tags = {
    Name = var.enviroment_name
  }
}

output "subnet_id" {
  value = aws_subnet.public.id
}